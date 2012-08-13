import sys
from gluster import *

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
	dl.unwind_lookup(frame,cookie,this,op_ret,op_errno,
					 inode,buf,xdata,postparent)
	return 0

class xlator ():
	def __init__ (self, xl):
		dl.set_lookup_fop(xl,lookup_fop)
		dl.set_lookup_cbk(xl,lookup_cbk)

