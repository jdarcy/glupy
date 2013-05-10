This is just the very start for a GlusterFS[1] meta-translator that will
allow translator code to be written in Python.  It's based on the standard
Python embedding (not extending) techniques, plus a dash of the ctypes module.
The interface is a pretty minimal adaptation of the dispatches and callbacks
from the C API[2] to Python, as follows:

* Dispatch functions and callbacks must be defined on an "xlator" class
  derived from gluster.Translator so that they'll be auto-registered with
  the C translator during initialization.

* For each dispatch or callback function you want to intercept, you define a
  Python function using the xxx\_fop\_t or xxx\_cbk\_t decorator.

* The arguments for each operation are different, so you'll need to refer to
  the C API.  GlusterFS-specific types are used (though only loc\_t is fully
  defined so far) and type correctness is enforced by ctypes.

* If you do intercept a dispatch function, it is your responsibility to call
  xxx\_wind (like STACK\_WIND in the C API but operation-specific) to pass
  the request to the next translator.  If you do not intercept a function, it
  will default the same way as for C (pass through to the same operation with
  the same arguments on the first child translator).

* If you intercept a callback function, it is your responsibility to call
  xxx\_unwind (like STACK\_UNWIND\_STRICT in the C API) to pass the request back
  to the caller.

Note that you can also use ctypes to get at anything not explicitly exposed to
Python already.

If you're coming here because of the Linux Journal article, please note that
the code has evolved since that was written. The version that matches the
article is here:

https://github.com/jdarcy/glupy/tree/4bbae91ba459ea46ef32f2966562492e4ca9187a

* [1] http://www.gluster.org
* [2] http://hekafs.org/dist/xlator_api_2.html


Installation
------------

__1. Point Glupy at GlusterFS source dir__

First, update the path to your GlusterFS source directory in the Makefile.

It's the *_GLFS_SRC_* variable.

    $ vi Makefile

__2. Compile and install Glupy__

    $ make
    $ sudo make install

__3. Let Python find gluster.py__

Now copy gluster.py to some place in your PYTHONPATH.

On EL6/CentOS6 with GlusterFS compiled from git master, this would work:

    $ sudo cp gluster.py /usr/lib64/glusterfs/3git/xlator/features/

That's it, Glupy is now installed. :)


Using it
--------

This isn't yet quite as straight forward as it could be.

When you've created a Glupy based translator you want to use,
you'll need to manually edit your .vol file to include it.

Glupy comes with an example "negative lookup" translator
you can start with.  It's the _negative.py_ file in this repo.

To add a translator to your .vol file, open it in a text
editor then:

1. Add a new "volume" entry (copy an existing one)
2. Change the volume name to something unique
3. Change the "type" to be "features/glupy"

The filename of your translator (without the .py extension)
is passed to Glupy using the "module-name" option.

So, for the "negative lookup" example translator, it would
be something like this:

    $ sudo vi /var/lib/glusterd/nfs/nfs-server.vol

    volume myvolume-negative
        type features/glupy
        option module-name negative
        subvolumes myvolume-write-behind
    end-volume

The name on the "subvolume" line in your .vol file will
probably be different.  You just need to adjust it so it's
part of the chain of volumes.  Take a look through the
existing .vol file, noticing that each volume points to
the one before it.  Then adjust your new Glupy volume to
do the same (eg fit it in somewhere).

When that's all done you need to start Gluster manually,
telling it to use your new .vol file.  eg:

    $ sudo glusterfs -f /var/lib/glusterd/nfs/nfs-server.vol --debug

Things should now work normally. :)
