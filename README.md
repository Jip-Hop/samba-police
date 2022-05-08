# Samba Police

Report missing/mangled files shared via Samba (illegal filename characters, symlinks). Useful after AFP to SMB/CIFS migration, or to regularly check file compatibility with SMB.

SMB may mangle your filenames due to illegal characters (e.g. `" \ / : | < > * ?` or [names ending with a dot or space](https://bugzilla.samba.org/show_bug.cgi?id=11207)). Files may even be missing when accessing the share. For example in the case dangling symlinks. Since SMB version 2 symlinks will instead be dereferenced (target file will be served). Dangling symlinks will be missing... The behavior you get depends on the SMB config and files in question. It's not trivial to make a list of filenames which will cause problems.

If you want to be sure your files are safe to export via SMB, no files are missing and filenames aren't garbled, you should run Samba Police. Instead of trying to identify all possible scenarios which may cause issues, Samba Police will check if all files in the source directory are also present on the SMB share. It will report files which are missing (either completely missing or with mangled names). It's supposed to run on the SMB host.

You could run it once, to cleanup your filenames and make them compatible with SMB. For example when migrating from AFP to SMB. Or you could run it regularly (e.g. via CRON) to become aware of the files which won't be properly preserved when copied from the SMB share. This is especially useful when files in the SMB share are created/modified outside of SMB: directly on the host with Resilio, Syncthing etc. or if the share is also made available via NFS. Then incompatible files could end up in the SMB share again...

```
usage: samba-police.py [-h] --src SRC --smb SMB [--ignore IGNORE] [--symlinks]

Report missing/mangled files shared via Samba (illegal filename characters, symlinks).
Useful after AFP to SMB/CIFS migration, or to regularly check file compatibility with SMB.

You need to manually mount the SMB share with option serverino before calling this script.
E.g. on TrueNAS SCALE or Synology DSM 6 (as root):
mount.cifs //localhost/Share /mnt/samba-police -o ro,serverino,iocharset=utf8,vers=3.0,username=user

optional arguments:
  -h, --help       show this help message and exit
  --src SRC        path to source directory (should be an SMB share)
  --smb SMB        path to target directory (the source directory, but mounted locally via SMB)
  --ignore IGNORE  path to ignore file (newline separated list of names/paths to ignore)
  --symlinks       report all symlinks as missing (symlinks are skipped by default)
```