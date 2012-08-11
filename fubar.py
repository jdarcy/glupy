import sys
from ctypes import *
from glupy import *

class loc_t (Structure):
	_fields_ = [
		( "path",	c_char_p ),
		( "name",	c_char_p ),
		( "inode",	c_void_p ),
		( "parent",	c_void_p ),
		( "gfid", c_char * 16 ),
		( "pargfid", c_char * 16 )
	]

class xlator ():
	def lookup_fop (self, frame, this, loc, xdata):
		py_loc = loc_t.from_address(int(loc))
		print "lookup FOP: %s" % py_loc.path
		# TBD: get real child xl from init, pass it here
		wind_lookup(frame,0,loc,xdata)
	def lookup_cbk (self, frame, cookie, this, op_ret, op_errno,
			        inode, buf, xdata, postparent):
		try:
			print "lookup CBK: %d (%d)" % (op_ret, op_errno)
			unwind_lookup(frame,op_ret,op_errno,inode,buf,xdata,postparent)
		except:
			print sys.exc_info()
