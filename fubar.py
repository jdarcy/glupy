import sys
from ctypes import *

dl = CDLL("",RTLD_GLOBAL)

class call_frame_t (Structure):
	pass

class xlator_t (Structure):
	pass

class dict_t (Structure):
	pass

class loc_t (Structure):
	_fields_ = [
		( "path",	c_char_p ),
		( "name",	c_char_p ),
		( "inode",	c_void_p ),
		( "parent",	c_void_p ),
		( "gfid", c_char * 16 ),
		( "pargfid", c_char * 16 )
	]

class inode_t (Structure):
	pass

class iatt_t (Structure):
	pass

lookup_fop_t = CFUNCTYPE(c_int,
						 POINTER(call_frame_t), POINTER(xlator_t),
						 POINTER(loc_t), POINTER(dict_t))

lookup_cbk_t = CFUNCTYPE(c_int,
						 POINTER(call_frame_t), c_void_p, POINTER(xlator_t),
						 c_int, c_int, POINTER(inode_t),
						 POINTER(iatt_t), POINTER(dict_t), POINTER(iatt_t))

dl.set_lookup_fop.restype = None
dl.set_lookup_fop.argtypes = [ c_long, lookup_fop_t ]
dl.set_lookup_cbk.restype = None
dl.set_lookup_cbk.argtypes = [ c_long, lookup_cbk_t ]
dl.wind_lookup.restype = None
dl.wind_lookup.argtypes = [ POINTER(call_frame_t), POINTER(xlator_t),
						    POINTER(loc_t), POINTER(dict_t) ]
dl.unwind_lookup.restype = None
dl.unwind_lookup.argtypes = [ POINTER(call_frame_t), c_int, c_int,
							  POINTER(inode_t), POINTER(iatt_t),
							  POINTER(dict_t), POINTER(iatt_t) ]

@lookup_fop_t
def lookup_fop (frame, this, loc, xdata):
	print "lookup FOP: %s" % loc.contents.path
	# TBD: get real child xl from init, pass it here
	dl.wind_lookup(frame,POINTER(xlator_t)(),loc,xdata)
	return 0

@lookup_cbk_t
def lookup_cbk (frame, cookie, this, op_ret, op_errno,
				inode, buf, xdata, postparent):
	print "lookup CBK: %d (%d)" % (op_ret, op_errno)
	dl.unwind_lookup(frame,op_ret,op_errno,inode,buf,xdata,postparent)
	return 0

class xlator ():
	def __init__ (self, xl):
		dl.set_lookup_fop(xl,lookup_fop)
		dl.set_lookup_cbk(xl,lookup_cbk)

