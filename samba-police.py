#!/usr/bin/env python3

"""
Report missing/mangled files shared via Samba (illegal filename characters, symlinks).
Useful after AFP to SMB/CIFS migration, or to regularly check file compatibility with SMB.

You need to manually mount the SMB share with option serverino before calling this script.
E.g. on TrueNAS SCALE or Synology DSM 6 (as root):
mount.cifs //localhost/Share /mnt/samba-police -o ro,serverino,iocharset=utf8,vers=3.0,username=user
"""

from os import path, scandir
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path


def main():

    def path_argument_type(p):
        # Use strict=True to fail on non-existent paths
        return Path(p).absolute().resolve(strict=True)

    parser = ArgumentParser(
        formatter_class=RawDescriptionHelpFormatter, description=__doc__)

    parser.add_argument(
        "--src",
        type=path_argument_type,
        required=True,
        help="path to source directory (should be an SMB share)",
    )

    parser.add_argument(
        "--smb",
        type=path_argument_type,
        required=True,
        help="path to target directory (the source directory, but mounted locally via SMB)",
    )

    parser.add_argument(
        "--ignore",
        type=path_argument_type,
        required=False,
        help="path to ignore file (newline separated list of names/paths to ignore)",
    )

    parser.add_argument(
        "--symlinks",
        action="store_true",
        required=False,
        help="report all symlinks as missing (symlinks are skipped by default)"
    )

    def process_ignore_file(p, ignores):
        with open(p) as file:
            while (line := file.readline()):
                # Skip comments and lines containing only whitespace
                if not line.startswith("#") and not line.isspace():
                    # Remove trailing newline and add to ignores
                    ignores.add(line.rstrip("\n"))

    def get_relative_path(p):
        return path.join("/", path.relpath(p, args.src))
    
    def report(p):
        print(p)

    def traverse(top, mangled_top):
        # NOTE: printing mangled_top can lead to the following error:
        # UnicodeEncodeError: 'utf-8' codec can't encode character '\udce9' in position 117: surrogates not allowed
        # Therefore need to get rid of invalid characters (when printing only!)
        # print(top, "-->", mangled_top.encode("utf-8", "replace").decode("utf-8"))
        with scandir(top) as it:
            for entry in it:

                if entry.name in ignores:
                    # print("IGNORED", entry.name)
                    continue

                relative_path = get_relative_path(entry.path)

                if relative_path in ignores:
                    # print("IGNORED", relative_path)
                    continue

                # Parent directory couldn't be found via SMB (on previous iterations)
                # Hence all children should be reported as missing
                if mangled_top is False:
                    report(relative_path)
                    continue

                if entry.is_symlink():
                    # NOTE: Starting from SMB version 2, symlinks are not preserved when served via SMB
                    # If the symlink is not broken, SMB can follow the symlink and serve the file
                    # In that case a file will exist with the same name as the symlink
                    # but it will no longer be a symlink (file size will be larger)
                    # So symlinks are lost when backing up a directory via SMB

                    # NOTE: It's possible to create symlinks via SMB (and present them as symlink to clients),
                    # but these Minshall/French symlinks won't be actual symlinks on the SMB server
                    # This check will not report MF-symlinks because they work properly when presented via SMB
                    # Actually MF-symlinks have the opposite problem: the symlinks are 'lost' when files are
                    # copied directly from the SMB host (e.g. via SSH)

                    # Only report if specified via symlinks argument
                    if args.symlinks:
                        report(relative_path)
                    # Continue to next file (don't process symlinks further)
                    continue

                path_via_smb = path.join(mangled_top, entry.name)
                if path.exists(path_via_smb):
                    # File exists on SMB side, all good!
                    if entry.is_dir(follow_symlinks=False):
                        # It's a directory, traverse into it
                        traverse(entry.path, path_via_smb)
                    continue

                # If we made it until here, then this entry is missing when accessed via SMB
                report(relative_path)

                if entry.is_dir(follow_symlinks=False):
                    # All children of mangled directory would be reported as missing...
                    # Unless we use mangled name on next traversal!

                    # Default to False, so all children will report as missing if mangled dir can't be found via inode
                    new_mangled_path = False

                    # NOTE: Multiple files can have the same inode number (due to hardlinks)...
                    # Hardlinks aren't supported for directories
                    # So multiple directories can't have the same inode number (inside the same filesystem)
                    # "Each directory inode is allowed to appear once in exactly one parent directory and no more."
                    # https://teaching.idallen.com/dat2330/04f/notes/links_and_inodes.html
                    # So if we have a match, we can be sure it's the directory we're looking for

                    inode = entry.inode()

                    # Find mangled name via inode
                    # Variable mangled_top should not be False (or scandir will fail)
                    # This has already been checked above
                    with scandir(mangled_top) as smb_it:
                        for smb_entry in smb_it:
                            if inode == smb_entry.inode():
                                # Found the same dir on the SMB side!
                                new_mangled_path = smb_entry.path
                                # NOTE: encode new_mangled_path when printing only!
                                # print("FOUND new_mangled_path", new_mangled_path.encode("utf-8", "replace").decode("utf-8"))
                                break

                    # Always traverse into a directory (also if finding remapping candidate failed)
                    # That way children of this dir can be reported as missing
                    traverse(entry.path, new_mangled_path)

    args = parser.parse_args()
    ignores = set()

    if args.ignore:
        process_ignore_file(args.ignore, ignores)

    traverse(args.src, args.smb)


if __name__ == "__main__":
    main()
