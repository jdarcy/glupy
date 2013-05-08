import sys
import stat
from uuid import UUID
from time import strftime, localtime
from gluster import *
# This translator was written primarily to test the fop entry point definitions
# and structure definitions in 'gluster.py'.
# It is similar to the debug-trace translator, one of the already available
# translator types written in C, that logs the arguments passed to the fops and
# their corresponding cbk functions.

dl.get_id.restype = c_long
dl.get_id.argtypes = [ POINTER(call_frame_t) ]

dl.get_rootunique.restype = c_uint64
dl.get_rootunique.argtypes = [ POINTER(call_frame_t) ]

def uuid2str (gfid):
        return str(UUID(''.join(map("{:02x}".format, gfid))))


def st_mode_from_ia (prot, filetype):
        st_mode = 0
        type_bit = 0
        prot_bit = 0

        if filetype == IA_IFREG:
                type_bit = stat.S_IFREG
        elif filetype == IA_IFDIR:
                type_bit = stat.S_IFDIR
        elif filetype == IA_IFLNK:
                type_bit = stat.S_IFLNK
        elif filetype == IA_IFBLK:
                type_bit = stat.S_IFBLK
        elif filetype == IA_IFCHR:
                type_bit = stat.S_IFCHR
        elif filetype == IA_IFIFO:
                type_bit = stat.S_IFIFO
        elif filetype == IA_IFSOCK:
                type_bit = stat.S_IFSOCK
        elif filetype == IA_INVAL:
                pass


        if prot.suid:
                prot_bit |= stat.S_ISUID
        if prot.sgid:
                prot_bit |= stat.S_ISGID
        if prot.sticky:
                prot_bit |= stat.S_ISVTX

        if prot.owner.read:
                prot_bit |= stat.S_IRUSR
        if prot.owner.write:
                prot_bit |= stat.S_IWUSR
        if prot.owner.execn:
                prot_bit |= stat.S_IXUSR

        if prot.group.read:
                prot_bit |= stat.S_IRGRP
        if prot.group.write:
                prot_bit |= stat.S_IWGRP
        if prot.group.execn:
                prot_bit |= stat.S_IXGRP

        if prot.other.read:
                prot_bit |= stat.S_IROTH
        if prot.other.write:
                prot_bit |= stat.S_IWOTH
        if prot.other.execn:
                prot_bit |= stat.S_IXOTH

        st_mode = (type_bit | prot_bit)

        return st_mode


def trace_stat2str (buf):
        gfid = uuid2str(buf.contents.ia_gfid)
        mode = st_mode_from_ia(buf.contents.ia_prot, buf.contents.ia_type)
        atime_buf = strftime("[%b %d %H:%M:%S]",
                             localtime(buf.contents.ia_atime))
        mtime_buf = strftime("[%b %d %H:%M:%S]",
                             localtime(buf.contents.ia_mtime))
        ctime_buf = strftime("[%b %d %H:%M:%S]",
                             localtime(buf.contents.ia_ctime))
        return ("(gfid={:s}, ino={:d}, mode={:o}, nlink={:d}, uid ={:d}, "+
                "gid ={:d}, size={:d}, blocks={:d}, atime={:s}, mtime={:s}, "+
                "ctime={:s})").format(gfid, buf.contents.ia_no, mode,
                                      buf.contents.ia_nlink,
                                      buf.contents.ia_uid,
                                      buf.contents.ia_gid,
                                      buf.contents.ia_size,
                                      buf.contents.ia_blocks,
                                      atime_buf, mtime_buf,
                                      ctime_buf)

class xlator(Translator):

        def __init__(self, c_this):
                Translator.__init__(self, c_this)
                self.gfids = {}

        def lookup_fop(self, frame, this, loc, xdata):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                gfid = uuid2str(loc.contents.gfid)
                print("GLUPY TRACE LOOKUP FOP- {:d}: gfid={:s}; " +
                      "path={:s}").format(unique, gfid, loc.contents.path)
                self.gfids[key] = gfid
                dl.wind_lookup(frame, POINTER(xlator_t)(), loc, xdata)
                return 0

        def lookup_cbk(self, frame, cookie, this, op_ret, op_errno,
                       inode, buf, xdata, postparent):
                unique =dl.get_rootunique(frame)
                key =dl.get_id(frame)
                if op_ret == 0:
                        gfid = uuid2str(buf.contents.ia_gfid)
                        statstr = trace_stat2str(buf)
                        postparentstr = trace_stat2str(postparent)
                        print("GLUPY TRACE LOOKUP CBK- {:d}: gfid={:s}; "+
                              "op_ret={:d}; *buf={:s}; " +
                              "*postparent={:s}").format(unique, gfid,
                                                         op_ret, statstr,
                                                         postparentstr)
                else:
                        gfid = self.gfids[key]
                        print("GLUPY TRACE LOOKUP CBK - {:d}: gfid={:s};" +
                              " op_ret={:d}; op_errno={:d}").format(unique,
                                                                    gfid,
                                                                    op_ret,
                                                                    op_errno)
                del self.gfids[key]
                dl.unwind_lookup(frame, cookie, this, op_ret, op_errno,
                                 inode, buf, xdata, postparent)
                return 0

        def create_fop(self, frame, this, loc, flags, mode, umask, fd,
                       xdata):
                unique = dl.get_rootunique(frame)
                gfid = uuid2str(loc.contents.gfid)
                print("GLUPY TRACE CREATE FOP- {:d}: gfid={:s}; path={:s}; " +
                      "fd={:s}; flags=0{:o}; mode=0{:o}; " +
                      "umask=0{:o}").format(unique, gfid, loc.contents.path,
                                            fd, flags, mode, umask)
                dl.wind_create(frame, POINTER(xlator_t)(), loc, flags,mode,
                               umask, fd, xdata)
                return 0

        def create_cbk(self, frame, cookie, this, op_ret, op_errno, fd,
                       inode, buf, preparent, postparent, xdata):
                unique = dl.get_rootunique(frame)
                if op_ret >= 0:
                        gfid = uuid2str(inode.contents.gfid)
                        statstr = trace_stat2str(buf)
                        preparentstr = trace_stat2str(preparent)
                        postparentstr = trace_stat2str(postparent)
                        print("GLUPY TRACE CREATE CBK- {:d}: gfid={:s};" +
                              " op_ret={:d}; fd={:s}; *stbuf={:s}; " +
                              "*preparent={:s};" +
                              " *postparent={:s}").format(unique, gfid, op_ret,
                                                          fd, statstr,
                                                          preparentstr,
                                                          postparentstr)
                else:
                        print ("GLUPY TRACE CREATE CBK- {:d}: op_ret={:d}; " +
                              "op_errno={:d}").format(unique, op_ret, op_errno)
                dl.unwind_create(frame, cookie, this, op_ret, op_errno, fd,
                                 inode, buf, preparent, postparent, xdata)
                return 0

        def open_fop(self, frame, this, loc, flags, fd, xdata):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                gfid = uuid2str(loc.contents.inode.contents.gfid)
                print("GLUPY TRACE OPEN FOP- {:d}: gfid={:s}; path={:s}; "+
                      "flags={:d}; fd={:s}").format(unique, gfid,
                                                    loc.contents.path, flags,
                                                    fd)
                self.gfids[key] = gfid
                dl.wind_open(frame, POINTER(xlator_t)(), loc, flags, fd, xdata)
                return 0

        def open_cbk(self, frame, cookie, this, op_ret, op_errno, fd, xdata):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                gfid = self.gfids[key]
                print("GLUPY TRACE OPEN CBK- {:d}: gfid={:s}; op_ret={:d}; "
                      "op_errno={:d}; *fd={:s}").format(unique, gfid,
                                                        op_ret, op_errno, fd)
                del self.gfids[key]
                dl.unwind_open(frame, cookie, this, op_ret, op_errno, fd,
                               xdata)
                return 0

        def readv_fop(self, frame, this, fd, size, offset, flags, xdata):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                gfid = uuid2str(fd.contents.inode.contents.gfid)
                print("GLUPY TRACE READV FOP- {:d}: gfid={:s}; "+
                      "fd={:s}; size ={:d}; offset={:d}; " +
                      "flags=0{:x}").format(unique, gfid, fd, size, offset,
                                            flags)
                self.gfids[key] = gfid
                dl.wind_readv (frame, POINTER(xlator_t)(), fd, size, offset,
                               flags, xdata)
                return 0

        def readv_cbk(self, frame, cookie, this, op_ret, op_errno, vector,
                      count, buf, iobref, xdata):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                gfid = self.gfids[key]
                if op_ret >= 0:
                        statstr = trace_stat2str(buf)
                        print("GLUPY TRACE READV CBK- {:d}: gfid={:s}, "+
                              "op_ret={:d}; *buf={:s};").format(unique, gfid,
                                                                op_ret,
                                                                statstr)

                else:
                        print("GLUPY TRACE READV CBK- {:d}: gfid={:s}, "+
                              "op_ret={:d}; op_errno={:d}").format(unique,
                                                                   gfid,
                                                                   op_ret,
                                                                   op_errno)
                del self.gfids[key]
                dl.unwind_readv (frame, cookie, this, op_ret, op_errno,
                                 vector, count, buf, iobref, xdata)
                return 0

        def writev_fop(self, frame, this, fd, vector, count, offset, flags,
                       iobref, xdata):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                gfid = uuid2str(fd.contents.inode.contents.gfid)
                print("GLUPY TRACE  WRITEV FOP- {:d}: gfid={:s}; " +
                      "fd={:s}; count={:d}; offset={:d}; " +
                      "flags=0{:x}").format(unique, gfid, fd, count, offset,
                                            flags)
                self.gfids[key] = gfid
                dl.wind_writev(frame, POINTER(xlator_t)(), fd, vector, count,
                               offset, flags, iobref, xdata)
                return 0

        def writev_cbk(self, frame, cookie, this, op_ret, op_errno, prebuf,
                       postbuf, xdata):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                if op_ret >= 0:
                        preopstr = trace_stat2str(prebuf)
                        postopstr = trace_stat2str(postbuf)
                        print("GLUPY TRACE WRITEV CBK- {:d}: op_ret={:d}; " +
                              "*prebuf={:s}; " +
                              "*postbuf={:s}").format(unique, op_ret, preopstr,
                                                      postopstr)
                else:
                        gfid = self.gfids[key]
                        print("GLUPY TRACE WRITEV CBK- {:d}: gfid={:s}; "+
                              "op_ret={:d}; op_errno={:d}").format(unique,
                                                                   gfid,
                                                                   op_ret,
                                                                   op_errno)
                del self.gfids[key]
                dl.unwind_writev (frame, cookie, this, op_ret, op_errno,
                                  prebuf, postbuf, xdata)
                return 0

        def opendir_fop(self, frame, this, loc, fd, xdata):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                gfid = uuid2str(loc.contents.inode.contents.gfid)
                print("GLUPY TRACE OPENDIR FOP- {:d}: gfid={:s}; path={:s}; "+
                      "fd={:s}").format(unique, gfid, loc.contents.path, fd)
                self.gfids[key] = gfid
                dl.wind_opendir(frame, POINTER(xlator_t)(), loc, fd, xdata)
                return 0

        def opendir_cbk(self, frame, cookie, this, op_ret, op_errno, fd,
                        xdata):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                gfid = self.gfids[key]
                print("GLUPY TRACE OPENDIR CBK- {:d}: gfid={:s}; op_ret={:d};"+
                      " op_errno={:d}; fd={:s}").format(unique, gfid, op_ret,
                                                        op_errno, fd)
                del self.gfids[key]
                dl.unwind_opendir(frame, cookie, this, op_ret, op_errno,
                                  fd, xdata)
                return 0

        def readdir_fop(self, frame, this, fd, size, offset, xdata):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                gfid = uuid2str(fd.contents.inode.contents.gfid)
                print("GLUPY TRACE READDIR FOP- {:d}:  gfid={:s}; fd={:s}; " +
                      "size={:d}; offset={:d}").format(unique, gfid, fd, size,
                                                       offset)
                self.gfids[key] = gfid
                dl.wind_readdir(frame, POINTER(xlator_t)(), fd, size, offset,
                                xdata)
                return 0

        def readdir_cbk(self, frame, cookie, this, op_ret, op_errno, buf,
                        xdata):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                gfid = self.gfids[key]
                print("GLUPY TRACE READDIR CBK- {:d}: gfid={:s}; op_ret={:d};"+
                      " op_errno={:d}").format(unique, gfid, op_ret, op_errno)
                del self.gfids[key]
                dl.unwind_readdir(frame, cookie, this, op_ret, op_errno, buf,
                                  xdata)
                return 0

        def readdirp_fop(self, frame, this, fd, size, offset, dictionary):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                gfid = uuid2str(fd.contents.inode.contents.gfid)
                print("GLUPY TRACE READDIR FOP- {:d}: gfid={:s}; fd={:s}; "+
                      " size={:d}; offset={:d}").format(unique, gfid, fd, size,
                      offset)
                self.gfids[key] = gfid
                dl.wind_readdirp(frame, POINTER(xlator_t)(), fd, size, offset,
                                 dictionary)
                return 0

        def readdirp_cbk(self, frame, cookie, this, op_ret, op_errno, buf,
                         xdata):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                gfid = self.gfids[key]
                print("GLUPY TRACE READDIRP CBK- {:d}: gfid={:s}; "+
                      "op_ret={:d}; op_errno={:d}").format(unique, gfid,
                                                           op_ret, op_errno)
                del self.gfids[key]
                dl.unwind_readdirp(frame, cookie, this, op_ret, op_errno, buf,
                                  xdata)
                return 0

        def mkdir_fop(self, frame, this, loc, mode, umask, xdata):
                unique = dl.get_rootunique(frame)
                gfid = uuid2str(loc.contents.inode.contents.gfid)
                print("GLUPY TRACE MKDIR FOP- {:d}: gfid={:s}; path={:s}; " +
                      "mode={:d}; umask=0{:o}").format(unique, gfid,
                                                       loc.contents.path, mode,
                                                       umask)
                dl.wind_mkdir(frame, POINTER(xlator_t)(), loc, mode, umask,
                              xdata)
                return 0

        def mkdir_cbk(self, frame, cookie, this, op_ret, op_errno, inode, buf,
                      preparent, postparent,  xdata):
                unique = dl.get_rootunique(frame)
                if op_ret == 0:
                        gfid = uuid2str(inode.contents.gfid)
                        statstr = trace_stat2str(buf)
                        preparentstr = trace_stat2str(preparent)
                        postparentstr = trace_stat2str(postparent)
                        print("GLUPY TRACE MKDIR CBK- {:d}: gfid={:s}; "+
                              "op_ret={:d}; *stbuf={:s}; *prebuf={:s}; "+
                              "*postbuf={:s} ").format(unique, gfid, op_ret,
                                                       statstr,
                                                       preparentstr,
                                                       postparentstr)
                else:
                        print("GLUPY TRACE MKDIR CBK- {:d}:  op_ret={:d}; "+
                              "op_errno={:d}").format(unique, op_ret, op_errno)
                dl.unwind_mkdir(frame, cookie, this, op_ret, op_errno, inode,
                                buf, preparent, postparent, xdata)
                return 0

        def rmdir_fop(self, frame, this, loc, flags, xdata):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                gfid = uuid2str(loc.contents.inode.contents.gfid)
                print("GLUPY TRACE RMDIR FOP- {:d}: gfid={:s}; path={:s}; "+
                      "flags={:d}").format(unique, gfid, loc.contents.path,
                                           flags)
                self.gfids[key] = gfid
                dl.wind_rmdir(frame, POINTER(xlator_t)(), loc, flags, xdata)
                return 0

        def rmdir_cbk(self, frame, cookie, this, op_ret, op_errno, preparent,
                      postparent, xdata):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                gfid = self.gfids[key]
                if op_ret == 0:
                        preparentstr = trace_stat2str(preparent)
                        postparentstr = trace_stat2str(postparent)
                        print("GLUPY TRACE RMDIR CBK- {:d}: gfid={:s}; "+
                              "op_ret={:d}; *prebuf={:s}; "+
                              "*postbuf={:s}").format(unique, gfid, op_ret,
                                                      preparentstr,
                                                      postparentstr)
                else:
                        print("GLUPY TRACE RMDIR CBK- {:d}: gfid={:s}; "+
                              "op_ret={:d}; op_errno={:d}").format(unique,
                                                                   gfid,
                                                                   op_ret,
                                                                   op_errno)
                del self.gfids[key]
                dl.unwind_rmdir(frame, cookie, this, op_ret, op_errno,
                                preparent, postparent, xdata)
                return 0

        def stat_fop(self, frame, this, loc, xdata):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                gfid = uuid2str(loc.contents.inode.contents.gfid)
                print("GLUPY TRACE STAT FOP- {:d}: gfid={:s}; " +
                      " path={:s}").format(unique, gfid, loc.contents.path)
                self.gfids[key] = gfid
                dl.wind_stat(frame, POINTER(xlator_t)(), loc, xdata)
                return 0

        def stat_cbk(self, frame, cookie, this, op_ret, op_errno, buf,
                     xdata):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                gfid = self.gfids[key]
                if op_ret == 0:
                        statstr = trace_stat2str(buf)
                        print("GLUPY TRACE STAT CBK- {:d}: gfid={:s}; "+
                              "op_ret={:d};  *buf={:s};").format(unique,
                                                                 gfid,
                                                                 op_ret,
                                                                 statstr)
                else:
                        print("GLUPY TRACE STAT CBK- {:d}: gfid={:s}; "+
                              "op_ret={:d}; op_errno={:d}").format(unique,
                                                                   gfid,
                                                                   op_ret,
                                                                   op_errno)
                del self.gfids[key]
                dl.unwind_stat(frame, cookie, this, op_ret, op_errno,
                               buf, xdata)
                return 0

        def fstat_fop(self, frame, this, fd, xdata):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                gfid = uuid2str(fd.contents.inode.contents.gfid)
                print("GLUPY TRACE FSTAT FOP- {:d}:  gfid={:s}; " +
                      "fd={:s}").format(unique, gfid, fd)
                self.gfids[key] = gfid
                dl.wind_fstat(frame, POINTER(xlator_t)(), fd, xdata)
                return 0

        def fstat_cbk(self, frame, cookie, this, op_ret, op_errno, buf,
                      xdata):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                gfid = self.gfids[key]
                if op_ret == 0:
                        statstr = trace_stat2str(buf)
                        print("GLUPY TRACE FSTAT CBK- {:d}: gfid={:s} "+
                              " op_ret={:d}; *buf={:s}").format(unique,
                                                                gfid,
                                                                op_ret,
                                                                statstr)
                else:
                        print("GLUPY TRACE FSTAT CBK- {d}: gfid={:s} "+
                              "op_ret={:d}; op_errno={:d}").format(unique.
                                                                   gfid,
                                                                   op_ret,
                                                                   op_errno)
                del self.gfids[key]
                dl.unwind_fstat(frame, cookie, this, op_ret, op_errno,
                                buf, xdata)
                return 0

        def statfs_fop(self, frame, this, loc, xdata):
                unique = dl.get_rootunique(frame)
                if loc.contents.inode:
                        gfid = uuid2str(loc.contents.inode.contents.gfid)
                else:
                        gfid = "0"
                print("GLUPY TRACE STATFS FOP- {:d}: gfid={:s}; "+
                      "path={:s}").format(unique, gfid, loc.contents.path)
                dl.wind_statfs(frame, POINTER(xlator_t)(), loc, xdata)
                return 0

        def statfs_cbk(self, frame, cookie, this, op_ret, op_errno, buf,
                       xdata):
                unique = dl.get_rootunique(frame)
                if op_ret == 0:
                        #TBD: print buf (pointer to an iovec type object)
                        print("GLUPY TRACE STATFS CBK {:d}: "+
                              "op_ret={:d}").format(unique, op_ret)
                else:
                        print("GLUPY TRACE STATFS CBK-  {:d}"+
                              "op_ret={:d}; op_errno={:d}").format(unique,
                                                                   op_ret,
                                                                   op_errno)
                dl.unwind_statfs(frame, cookie, this, op_ret, op_errno,
                                 buf, xdata)
                return 0

        def getxattr_fop(self, frame, this, loc, name, xdata):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                gfid = uuid2str(loc.contents.inode.contents.gfid)
                print("GLUPY TRACE GETXATTR FOP- {:d}: gfid={:s}; path={:s};"+
                      " name={:s}").format(unique, gfid, loc.contents.path,
                                           name)
                self.gfids[key]=gfid
                dl.wind_getxattr(frame, POINTER(xlator_t)(), loc, name, xdata)
                return 0

        def getxattr_cbk(self, frame, cookie, this, op_ret, op_errno,
                         dictionary, xdata):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                gfid = self.gfids[key]
                print("GLUPY TRACE GETXATTR CBK- {:d}: gfid={:s}; "+
                      "op_ret={:d}; op_errno={:d}; "+
                      " dictionary={:s}").format(unique, gfid, op_ret, op_errno,
                      dictionary)
                del self.gfids[key]
                dl.unwind_getxattr(frame, cookie, this, op_ret, op_errno,
                                   dictionary, xdata)
                return 0

        def fgetxattr_fop(self, frame, this, fd, name, xdata):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                gfid = uuid2str(fd.contents.inode.contents.gfid)
                print("GLUPY TRACE FGETXATTR FOP- {:d}: gfid={:s}; fd={:s}; "+
                      "name={:s}").format(unique, gfid, fd, name)
                self.gfids[key] = gfid
                dl.wind_fgetxattr(frame, POINTER(xlator_t)(), fd, name, xdata)
                return 0

        def fgetxattr_cbk(self, frame, cookie, this, op_ret, op_errno,
                          dictionary, xdata):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                gfid = self.gfids[key]
                print("GLUPY TRACE FGETXATTR CBK- {:d}: gfid={:s}; "+
                      "op_ret={:d}; op_errno={:d};"+
                      " dictionary={:s}").format(unique, gfid, op_ret,
                                                 op_errno, dictionary)
                del self.gfids[key]
                dl.unwind_fgetxattr(frame, cookie, this, op_ret, op_errno,
                                    dictionary, xdata)
                return 0

        def setxattr_fop(self, frame, this, loc, dictionary, flags, xdata):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                gfid = uuid2str(loc.contents.inode.contents.gfid)
                print("GLUPY TRACE SETXATTR FOP- {:d}:  gfid={:s}; path={:s};"+
                      " flags={:d}").format(unique, gfid, loc.contents.path,
                                            flags)
                self.gfids[key] = gfid
                dl.wind_setxattr(frame, POINTER(xlator_t)(), loc, dictionary,
                                 flags, xdata)
                return 0

        def setxattr_cbk(self, frame, cookie, this, op_ret, op_errno, xdata):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                gfid = self.gfids[key]
                print("GLUPY TRACE SETXATTR CBK- {:d}: gfid={:s}; "+
                      "op_ret={:d}; op_errno={:d}").format(unique, gfid,
                                                           op_ret, op_errno)
                del self.gfids[key]
                dl.unwind_setxattr(frame, cookie, this, op_ret, op_errno,
                                   xdata)
                return 0

        def fsetxattr_fop(self, frame, this, fd, dictionary, flags, xdata):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                gfid = uuid2str(fd.contents.inode.contents.gfid)
                print("GLUPY TRACE FSETXATTR FOP- {:d}: gfid={:s}; fd={:p}; "+
                      "flags={:d}").format(unique, gfid, fd, flags)
                self.gfids[key] = gfid
                dl.wind_fsetxattr(frame, POINTER(xlator_t)(), fd, dictionary,
                                  flags, xdata)
                return 0

        def fsetxattr_cbk(self, frame, cookie, this, op_ret, op_errno, xdata):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                gfid = self.gfids[key]
                print("GLUPY TRACE FSETXATTR CBK- {:d}: gfid={:s};  "+
                      "op_ret={:d}; op_errno={:d}").format(unique, gfid,
                                                           op_ret, op_errno)
                del self.gfids[key]
                dl.unwind_fsetxattr(frame, cookie, this, op_ret, op_errno,
                                   xdata)
                return 0

        def removexattr_fop(self, frame, this, loc, name, xdata):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                gfid = uuid2str(loc.contents.inode.contents.gfid)
                print("GLUPY TRACE REMOVEXATTR FOP- {:d}:  gfid={:s}; "+
                      "path={:s}; name={:s}").format(unique, gfid,
                                                     loc.contents.path,
                                                     name)
                self.gfids[key] = gfid
                dl.wind_removexattr(frame, POINTER(xlator_t)(), loc, name,
                                    xdata)
                return 0

        def removexattr_cbk(self, frame, cookie, this, op_ret, op_errno,
                            xdata):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                gfid = self.gfids[key]
                print("GLUPY TRACE REMOVEXATTR CBK- {:d}: gfid={:s} "+
                      " op_ret={:d}; op_errno={:d}").format(unique, gfid,
                                                            op_ret, op_errno)
                del self.gfids[key]
                dl.unwind_removexattr(frame, cookie, this, op_ret, op_errno,
                                      xdata)
                return 0

        def link_fop(self, frame, this, oldloc, newloc, xdata):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                if (newloc.contents.inode):
                        newgfid = uuid2str(newloc.contents.inode.contents.gfid)
                else:
                        newgfid = "0"
                oldgfid = uuid2str(oldloc.contents.inode.contents.gfid)
                print("GLUPY TRACE LINK FOP-{:d}: oldgfid={:s}; oldpath={:s};"+
                      "newgfid={:s};"+
                      "newpath={:s}").format(unique, oldgfid,
                                             oldloc.contents.path,
                                             newgfid,
                                             newloc.contents.path)
                self.gfids[key] =  oldgfid
                dl.wind_link(frame, POINTER(xlator_t)(), oldloc, newloc,
                             xdata)
                return 0

        def link_cbk(self, frame, cookie, this, op_ret, op_errno, inode, buf,
                     preparent, postparent, xdata):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                gfid = self.gfids[key]
                if op_ret == 0:
                        statstr = trace_stat2str(buf)
                        preparentstr = trace_stat2str(preparent)
                        postparentstr = trace_stat2str(postparent)
                        print("GLUPY TRACE LINK CBK- {:d}: op_ret={:d} "+
                              "*stbuf={:s}; *prebuf={:s}; "+
                              "*postbuf={:s} ").format(unique, op_ret, statstr,
                                                       preparentstr,
                                                       postparentstr)
                else:
                        print("GLUPY TRACE LINK CBK- {:d}: gfid={:s}; "+
                              "op_ret={:d}; "+
                              "op_errno={:d}").format(unique, gfid,
                                                      op_ret, op_errno)
                del self.gfids[key]
                dl.unwind_link(frame, cookie, this, op_ret, op_errno, inode,
                               buf, preparent, postparent, xdata)
                return 0

        def unlink_fop(self, frame, this, loc, xflag, xdata):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                gfid = uuid2str(loc.contents.inode.contents.gfid)
                print("GLUPY TRACE UNLINK FOP- {:d}; gfid={:s}; path={:s}; "+
                      "flag={:d}").format(unique, gfid, loc.contents.path,
                                          xflag)
                self.gfids[key] = gfid
                dl.wind_unlink(frame, POINTER(xlator_t)(), loc, xflag,
                               xdata)
                return 0

        def unlink_cbk(self, frame, cookie, this, op_ret, op_errno,
                       preparent, postparent, xdata):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                gfid = self.gfids[key]
                if op_ret == 0:
                        preparentstr = trace_stat2str(preparent)
                        postparentstr = trace_stat2str(postparent)
                        print("GLUPY TRACE UNLINK CBK- {:d}: gfid ={:s}; "+
                              "op_ret={:d}; *prebuf={:s}; "+
                              "*postbuf={:s} ").format(unique, gfid, op_ret,
                                                       preparentstr,
                                                       postparentstr)
                else:
                        print("GLUPY TRACE UNLINK CBK: {:d}: gfid ={:s}; "+
                              "op_ret={:d}; "+
                              "op_errno={:d}").format(unique, gfid, op_ret,
                                                      op_errno)
                del self.gfids[key]
                dl.unwind_unlink(frame, cookie, this, op_ret, op_errno,
                                 preparent, postparent, xdata)
                return 0

        def readlink_fop(self, frame, this, loc, size, xdata):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                gfid = uuid2str(loc.contents.inode.contents.gfid)
                print("GLUPY TRACE READLINK FOP- {:d}:  gfid={:s}; path={:s};"+
                      " size={:d}").format(unique, gfid, loc.contents.path,
                                           size)
                self.gfids[key] = gfid
                dl.wind_readlink(frame, POINTER(xlator_t)(), loc, size,
                               xdata)
                return 0

        def readlink_cbk(self, frame, cookie, this, op_ret, op_errno,
                         buf, stbuf, xdata):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                gfid  = self.gfids[key]
                if op_ret == 0:
                        statstr = trace_stat2str(stbuf)
                        print("GLUPY TRACE READLINK CBK- {:d}: gfid={:s} "+
                              " op_ret={:d}; op_errno={:d}; *prebuf={:s}; "+
                              "*postbuf={:s} ").format(unique, gfid,
                                                       op_ret, op_errno,
                                                       buf, statstr)
                else:
                        print("GLUPY TRACE READLINK CBK- {:d}: gfid={:s} "+
                              " op_ret={:d}; op_errno={:d}").format(unique,
                                                                    gfid,
                                                                    op_ret,
                                                                    op_errno)
                del self.gfids[key]
                dl.unwind_readlink(frame, cookie, this, op_ret, op_errno, buf,
                                   stbuf, xdata)
                return 0

        def symlink_fop(self, frame, this, linkpath, loc, umask, xdata):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                gfid = uuid2str(loc.contents.inode.contents.gfid)
                print("GLUPY TRACE SYMLINK FOP- {:d}: gfid={:s}; "+
                      "linkpath={:s}; path={:s};"+
                      "umask=0{:o}").format(unique, gfid, linkpath,
                                            loc.contents.path, umask)
                self.gfids[key] = gfid
                dl.wind_symlink(frame, POINTER(xlator_t)(), linkpath, loc,
                                umask, xdata)
                return 0

        def symlink_cbk(self, frame, cookie, this, op_ret, op_errno,
                        inode, buf, preparent, postparent, xdata):
                unique = dl.get_rootunique(frame)
                key = dl.get_id(frame)
                gfid = self.gfids[key]
                if op_ret == 0:
                        statstr = trace_stat2str(buf)
                        preparentstr = trace_stat2str(preparent)
                        postparentstr = trace_stat2str(postparent)
                        print("GLUPY TRACE SYMLINK CBK- {:d}: gfid={:s}; "+
                              "op_ret={:d}; *stbuf={:s}; *preparent={:s}; "+
                              "*postparent={:s}").format(unique, gfid,
                                                         op_ret, statstr,
                                                         preparentstr,
                                                         postparentstr)
                else:
                        print("GLUPY TRACE SYMLINK CBK- {:d}: gfid={:s}; "+
                              "op_ret={:d}; op_errno={:d}").format(unique,
                                                                   gfid,
                                                                   op_ret,
                                                                   op_errno)
                del self.gfids[key]
                dl.unwind_symlink(frame, cookie, this, op_ret, op_errno,
                                  inode, buf, preparent, postparent, xdata)
                return 0
