import sys
from ctypes import *

dl = CDLL("",RTLD_GLOBAL)

class call_frame_t (Structure):
	pass

class dict_t (Structure):
	pass

class fd_t (Structure):
	pass

class iatt_t (Structure):
	pass

class inode_t (Structure):
	pass

class loc_t (Structure):
	_fields_ = [
		( "path",	c_char_p ),
		( "name",	c_char_p ),
		( "inode",	c_void_p ),
		( "parent",	c_void_p ),
		# Not quite correct, but easier to manipulate.
		( "gfid", c_uint * 4 ),
		( "pargfid", c_uint * 4 ),
	]

class xlator_t (Structure):
	pass

def _init_op (a_class, fop, cbk, wind, unwind):
		# Decorators, used by translators. We could pass the signatures as
		# parameters, but it's actually kind of nice to keep them around for
		# inspection.
		a_class.fop_type = apply(CFUNCTYPE,a_class.fop_sig)
		a_class.cbk_type = apply(CFUNCTYPE,a_class.cbk_sig)
		# Dispatch function.
		fop.restype = None
		fop.argtypes = [ c_long, a_class.fop_type ]
		# Callback function.
		cbk.restype = None
		cbk.argtypes = [ c_long, a_class.cbk_type ]
		# STACK_WIND function.
		wind.restype = None
		wind.argtypes = list(a_class.fop_sig[1:])
		# STACK_UNWIND function.
		unwind.restype = None
		unwind.argtypes = list(a_class.cbk_sig[1:])

class OpLookup:
		fop_sig = (c_int, POINTER(call_frame_t), POINTER(xlator_t),
				   POINTER(loc_t), POINTER(dict_t))
		cbk_sig = (c_int, POINTER(call_frame_t), c_long, POINTER(xlator_t),
				   c_int, c_int, POINTER(inode_t), POINTER(iatt_t),
				   POINTER(dict_t), POINTER(iatt_t))
_init_op (OpLookup, dl.set_lookup_fop, dl.set_lookup_cbk,
					dl.wind_lookup,    dl.unwind_lookup)

class OpCreate:
		fop_sig = (c_int, POINTER(call_frame_t), POINTER(xlator_t),
				   POINTER(loc_t), c_int, c_uint, c_uint, POINTER(fd_t),
				   POINTER(dict_t))
		cbk_sig = (c_int, POINTER(call_frame_t), c_long, POINTER(xlator_t),
				   c_int, c_int, POINTER(fd_t), POINTER(inode_t),
				   POINTER(iatt_t), POINTER(iatt_t), POINTER(iatt_t),
				   POINTER(dict_t))
_init_op (OpCreate, dl.set_create_fop, dl.set_create_cbk,
					dl.wind_create,    dl.unwind_create)

