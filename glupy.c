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

int32_t
glupy_lookup_cbk (call_frame_t *frame, void *cookie, xlator_t *this,
                  int32_t op_ret, int32_t op_errno, inode_t *inode,
                  struct iatt *buf, dict_t *xdata, struct iatt *postparent)
{
        glupy_private_t *priv = this->private;

        if (!priv->cbks[GLUPY_LOOKUP]) {
                goto unwind;
        }

        return ((fop_lookup_cbk_t)(priv->cbks[GLUPY_LOOKUP]))(
                frame, cookie, this, op_ret, op_errno,
                inode, buf, xdata, postparent);
        
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
        PyObject        *args = NULL;
        PyObject        *result = NULL;

        if (!priv->fops[GLUPY_LOOKUP]) {
                goto wind;
        }

        args = Py_BuildValue("kkkk",frame,this,loc,xdata);
        if (!args) {
                goto wind;
        }

        result = PyObject_CallObject(priv->fops[GLUPY_LOOKUP],args);
        Py_DECREF(args);
        if (!result) {
                goto wind;
        }

        /* TBD: propagate return value? */
        Py_DECREF(result);
        return 0;

wind:
        STACK_WIND (frame, glupy_lookup_cbk, FIRST_CHILD(this),
                    FIRST_CHILD(this)->fops->lookup, loc, xdata);
        return 0;
}

PyObject *
wind_lookup (PyObject *self, PyObject *args)
{
        long             py_frame;
        long             py_xl;
        long             py_loc;
        long             py_xdata;
        xlator_t        *this = THIS;
        xlator_t        *xl = FIRST_CHILD(this);

        if (!PyArg_ParseTuple(args,"kkkk",&py_frame,&py_xl,&py_loc,&py_xdata)) {
                gf_log (this->name, GF_LOG_ERROR, "bad %s call", __func__);
                xl = FIRST_CHILD(this);
                goto err;
        }

        if (py_xl) {
                xl = (xlator_t *)py_xl;
        }
        else {
                xl = FIRST_CHILD(this);
        }

        STACK_WIND (((call_frame_t *)py_frame), glupy_lookup_cbk, xl,
                    xl->fops->lookup, (loc_t *)py_loc, (dict_t *)py_xdata);
err:
        return Py_None;
}

void
unwind_lookup (call_frame_t *frame, int32_t op_ret, int32_t op_errno,
               inode_t *inode, struct iatt *buf,
               dict_t *xdata, struct iatt *postparent)
{
        STACK_UNWIND_STRICT(lookup,frame,op_ret,op_errno,
                            inode,buf,xdata,postparent);
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

void
fill_api_list (glupy_private_t *priv)
{
        int              i = 0;
        PyObject        *py_func = NULL;

        for (i = 0; i < GLUPY_N_FUNCS; ++i) {
                py_func = PyObject_GetAttrString(priv->py_xlator,
                                                 api_functions[i].fop_name);
                if (py_func) {
                        if (PyCallable_Check(py_func)) {
                                priv->fops[i] = py_func;
                        }
                        else {
                                Py_DECREF(py_func);
                        }
                }
                else {
                        PyErr_Clear();
                }
        }
}

static PyMethodDef GlupyMethods[] = {
        { "wind_lookup", wind_lookup, METH_VARARGS,
          "STACK_WIND for a lookup call" },
    {NULL, NULL, 0, NULL}
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
                Py_InitModule("glupy", GlupyMethods);
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

        fill_api_list(priv);
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
