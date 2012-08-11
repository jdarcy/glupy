This is just the very start for a GlusterFS[1] meta-translator that will
allow translator code to be written in Python.  It's based on the standard
Python embedding (not extending) techniques, plus a dash of the ctypes module.
The interface is a pretty minimal adaptation of the dispatches and callbacks
from the C API[2] to Python, as follows:

* You define a Python "xlator" class.

* On that class, you can define "xxx\_fop" and/or "xxx\_cbk" methods for the
  dispatch and callback parts of any call you want to intercept.

* The arguments for each operation are different, so you'll need to refer to
  the C API.  In most cases, pointers will be passed as longs and you'll need
  to use ctypes.from\_address yourself to convert into actual structures if/when
  you need to (there's an example of this for loc\_t in the code).

* If you do intercept a dispatch function, it is your responsibility to call
  xxx\_wind (like STACK\_WIND in the C API but operation-specific) to pass
  the request to the next translator.  If you do not intercept a function, it
  will default the same way as for C (pass through to the same operation with
  the same arguments on the first child translator).

* If you intercept a callback function, it is your responsibility to call
  xxx\_unwind (like STACK\_UNWIND\_STRICT in the C API) to pass the request back
  to the caller.

So far only the lookup operation is handled this way.  Now that the basic
infrastructure is in place, adding more functions should be very quick, though
with that much boilerplate I might pause to write a code generator.  I also
plan to add structure definitions and interfaces for some of the utility
functions in libglusterfs (especially those having to do with inode and fd
context) in the fairly near future.  Note that you can also use ctypes to get
at anything not explicitly exposed to Pyton already.

[1] http://www.gluster.org
[2] http://hekafs.org/dist/xlator\_api\_2.html
