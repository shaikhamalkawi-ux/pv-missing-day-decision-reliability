import ctypes, ctypes.util, os, sys
src=sys.argv[1]; dst=sys.argv[2]
lib=ctypes.CDLL(ctypes.util.find_library('archive') or 'libarchive.so')
lib.archive_read_new.restype=ctypes.c_void_p
for fn in ['archive_read_support_filter_all','archive_read_support_format_all']:
    getattr(lib,fn).argtypes=[ctypes.c_void_p]; getattr(lib,fn).restype=ctypes.c_int
lib.archive_read_open_filename.argtypes=[ctypes.c_void_p,ctypes.c_char_p,ctypes.c_size_t];lib.archive_read_open_filename.restype=ctypes.c_int
lib.archive_read_next_header.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_void_p)];lib.archive_read_next_header.restype=ctypes.c_int
lib.archive_entry_pathname.argtypes=[ctypes.c_void_p];lib.archive_entry_pathname.restype=ctypes.c_char_p
lib.archive_entry_filetype.argtypes=[ctypes.c_void_p];lib.archive_entry_filetype.restype=ctypes.c_uint
lib.archive_read_data.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t];lib.archive_read_data.restype=ctypes.c_ssize_t
lib.archive_error_string.argtypes=[ctypes.c_void_p];lib.archive_error_string.restype=ctypes.c_char_p
lib.archive_read_free.argtypes=[ctypes.c_void_p];lib.archive_read_free.restype=ctypes.c_int
ARCHIVE_OK=0; ARCHIVE_EOF=1; AE_IFDIR=0o040000
os.makedirs(dst,exist_ok=True)
a=lib.archive_read_new();lib.archive_read_support_filter_all(a);lib.archive_read_support_format_all(a)
if lib.archive_read_open_filename(a,src.encode(),10240)!=ARCHIVE_OK: raise RuntimeError(lib.archive_error_string(a).decode())
ent=ctypes.c_void_p();n=0
while True:
    rc=lib.archive_read_next_header(a,ctypes.byref(ent))
    if rc==ARCHIVE_EOF: break
    if rc!=ARCHIVE_OK: raise RuntimeError(lib.archive_error_string(a).decode())
    p=lib.archive_entry_pathname(ent).decode('utf-8','replace'); norm=os.path.normpath(p).lstrip('/\\')
    if norm.startswith('..'): raise RuntimeError('unsafe archive path '+p)
    out=os.path.join(dst,norm)
    if lib.archive_entry_filetype(ent)==AE_IFDIR or p.endswith('/'): os.makedirs(out,exist_ok=True);continue
    os.makedirs(os.path.dirname(out),exist_ok=True)
    with open(out,'wb') as f:
        buf=ctypes.create_string_buffer(1<<20)
        while True:
            z=lib.archive_read_data(a,buf,len(buf))
            if z==0:break
            if z<0:raise RuntimeError(lib.archive_error_string(a).decode())
            f.write(buf.raw[:z])
    n+=1
lib.archive_read_free(a);print(n)
