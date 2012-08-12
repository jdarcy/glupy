/*
  Copyright (c) 2012 Red Hat, Inc. <http://www.redhat.com>
  This file is part of GlusterFS.

  GlusterFS is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published
  by the Free Software Foundation; either version 3 of the License,
  or (at your option) any later version.

  GlusterFS is distributed in the hope that it will be useful, but
  WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
  General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program.  If not, see
  <http://www.gnu.org/licenses/>.
*/

#include <ctype.h>
#include <sys/uio.h>
#include <python2.6/Python.h>

#ifndef _CONFIG_H
#define _CONFIG_H
#include "config.h"
#endif

#include "glusterfs.h"
#include "xlator.h"
#include "logging.h"
#include "defaults.h"

#include "glupy.h"

pthread_key_t gil_init_key;

PyGILState_STATE
glupy_enter (void)
{
        if (!pthread_getspecific(gil_init_key)) {
                PyEval_ReleaseLock();
                (void)pthread_setspecific(gil_init_key,(void *)1);
        }

        return PyGILState_Ensure();
}

void
glupy_leave (PyGILState_STATE gstate)
{
        PyGILState_Release(gstate);
}

int32_t
glupy_lookup_cbk (call_frame_t *frame, void *cookie, xlator_t *this,
                  int32_t op_ret, int32_t op_errno, inode_t *inode,
                  struct iatt *buf, dict_t *xdata, struct iatt *postparent)
{
        glupy_private_t *priv = this->private;
        PyGILState_STATE gstate;
        int32_t ret;

        if (!priv->cbks[GLUPY_LOOKUP]) {
                goto unwind;
        }

        gstate = glupy_enter();
        ret = ((fop_lookup_cbk_t)(priv->cbks[GLUPY_LOOKUP]))(
                frame, cookie, this, op_ret, op_errno,
                inode, buf, xdata, postparent);
        glupy_leave(gstate);

        return ret;
        
unwind:
        STACK_UNWIND_STRICT (lookup, frame, op_ret, op_errno, inode, buf,
                             xdata, postparent);
        return 0;
}

int32_t
glupy_lookup (call_frame_t *frame, xlator_t *this, loc_t *loc,
              dict_t *xdata)
{
        glupy_private_t *priv = this->private;
        PyGILState_STATE gstate;
        int32_t ret;

        if (!priv->fops[GLUPY_LOOKUP]) {
                goto wind;
        }

        gstate = glupy_enter();
        ret = ((fop_lookup_t)(priv->fops[GLUPY_LOOKUP]))(
                frame, this, loc, xdata);
        glupy_leave(gstate);

        return ret;

wind:
        STACK_WIND (frame, glupy_lookup_cbk, FIRST_CHILD(this),
                    FIRST_CHILD(this)->fops->lookup, loc, xdata);
        return 0;
}

void
wind_lookup (call_frame_t *frame, xlator_t *xl, loc_t *loc, dict_t *xdata)
{
        
        xlator_t        *this = THIS;

        if (!xl || (xl == this)) {
                xl = FIRST_CHILD(this);
        }

        STACK_WIND(frame,glupy_lookup_cbk,xl,xl->fops->lookup,loc,xdata);
}

void
unwind_lookup (call_frame_t *frame, long cookie, xlator_t *this,
               int32_t op_ret, int32_t op_errno, inode_t *inode,
               struct iatt *buf, dict_t *xdata, struct iatt *postparent)
{
        STACK_UNWIND_STRICT(lookup,frame,op_ret,op_errno,
                            inode,buf,xdata,postparent);
}

void
set_lookup_fop (long py_this, fop_lookup_t fop)
{
        glupy_private_t *priv   = ((xlator_t *)py_this)->private;

        priv->fops[GLUPY_LOOKUP] = (long)fop;
}

void
set_lookup_cbk (long py_this, fop_lookup_cbk_t cbk)
{
        glupy_private_t *priv   = ((xlator_t *)py_this)->private;

        priv->cbks[GLUPY_LOOKUP] = (long)cbk;
}

#define GLUPY_API_FUNCTION(x)  { #x "_fop", #x "_cbk" }
struct {
        char    *fop_name;
        char    *cbk_name;
} api_functions[] = {
        GLUPY_API_FUNCTION(lookup),
};

int32_t
init (xlator_t *this)
{
	glupy_private_t         *priv           = NULL;
        char                    *module_name    = NULL;
        PyObject                *py_mod_name    = NULL;
        PyObject                *py_init_func   = NULL;
        PyObject                *py_args        = NULL;
        static gf_boolean_t      py_inited      = _gf_false;
        void *                   err_cleanup    = &&err_return;

        if (dict_get_str(this->options,"module-name",&module_name) != 0) {
                gf_log (this->name, GF_LOG_ERROR, "missing module-name");
                return -1;
        }

	priv = GF_CALLOC (1, sizeof (glupy_private_t), gf_glupy_mt_priv);
        if (!priv) {
                goto *err_cleanup;
        }
        this->private = priv;
        err_cleanup = &&err_free_priv;

        if (!py_inited) {
                Py_Initialize();
                PyEval_InitThreads();
                (void)pthread_key_create(&gil_init_key,NULL);
                (void)pthread_setspecific(gil_init_key,(void *)1);
                py_inited = _gf_true;
        }

        py_mod_name = PyString_FromString(module_name);
        if (!py_mod_name) {
                gf_log (this->name, GF_LOG_ERROR, "could not create name");
                goto *err_cleanup;
        }

        priv->py_module = PyImport_Import(py_mod_name);
        Py_DECREF(py_mod_name);
        if (!priv->py_module) {
                gf_log (this->name, GF_LOG_ERROR, "Python import failed");
                if (PyErr_Occurred()) {
                        PyErr_Print();
                }
                goto *err_cleanup;
        }
        err_cleanup = &&err_deref_module;

        py_init_func = PyObject_GetAttrString(priv->py_module, "xlator");
        if (!py_init_func || !PyCallable_Check(py_init_func)) {
                gf_log (this->name, GF_LOG_ERROR, "missing init func");
                goto *err_cleanup;
        }
        err_cleanup = &&err_deref_init;

        py_args = PyTuple_New(1);
        if (!py_args) {
                gf_log (this->name, GF_LOG_ERROR, "could not create args");
                goto *err_cleanup;
        }
        PyTuple_SetItem(py_args,0,PyLong_FromLong((long)this));

        /* TBD: pass in list of children */
        priv->py_xlator = PyObject_CallObject(py_init_func, py_args);
        Py_DECREF(py_args);
        if (!priv->py_xlator) {
                gf_log (this->name, GF_LOG_ERROR, "Python init failed");
                goto *err_cleanup;
        }
        gf_log (this->name, GF_LOG_INFO, "init returned %p", priv->py_xlator);

	return 0;

err_deref_init:
        Py_DECREF(py_init_func);
err_deref_module:
        Py_DECREF(priv->py_module);
err_free_priv:
        GF_FREE(priv);
err_return:
        return -1;
}

void
fini (xlator_t *this)
{
        int              i = 0;
	glupy_private_t *priv = this->private;

        if (!priv)
                return;
        for (i = 0; i < GLUPY_N_FUNCS; ++i) {
                if (priv->fops[i]) {
                        Py_DECREF(priv->fops[i]);
                }
                if (priv->cbks[i]) {
                        Py_DECREF(priv->fops[i]);
                }
        }
        Py_DECREF(priv->py_xlator);
        Py_DECREF(priv->py_module);
        this->private = NULL;
	GF_FREE (priv);

	return;
}

struct xlator_fops fops = {
        .lookup = glupy_lookup,
};

struct xlator_cbks cbks = {
};

struct volume_options options[] = {
	{ .key  = {NULL} },
};
