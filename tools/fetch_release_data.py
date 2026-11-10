#!/usr/bin/env python3
"""Restore the pinned release data for a source checkout; standard library only."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def restore(archive, destination, manifest, force=False):
    expected = manifest['data_archive']
    if archive.stat().st_size != expected['bytes'] or sha256(archive) != expected['sha256']:
        raise ValueError('Data archive size or SHA-256 does not match release-manifest.json')
    records = {entry['path']: entry for entry in manifest['data_files']}
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        if len(names) != len(set(names)) or set(names) != set(records):
            raise ValueError('Data archive member list does not match the release manifest')
        # Validate every member and collision before writing any destination file.
        for name in names:
            rel = PurePosixPath(name)
            if rel.is_absolute() or '..' in rel.parts or rel.parts[:2] != ('lunar_terrain', 'data'):
                raise ValueError(f'Unsafe archive path: {name}')
            target = destination.joinpath(*rel.parts)
            if not target.resolve().is_relative_to(destination.resolve()):
                raise ValueError(f'Path escapes destination: {name}')
            info = bundle.getinfo(name)
            entry = records[name]
            if info.file_size != entry['bytes']:
                raise ValueError(f'Unexpected member size: {name}')
            with bundle.open(name) as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != entry['sha256']:
                    raise ValueError(f'Member checksum failed: {name}')
            if target.exists() and not force and sha256(target) != entry['sha256']:
                raise ValueError(f'Refusing to replace modified data: {name}; use --force intentionally')
        for name in names:
            target = destination / name
            entry = records[name]
            if target.is_file() and sha256(target) == entry['sha256']:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as temp:
                temporary = Path(temp.name)
                try:
                    with bundle.open(name) as stream:
                        shutil.copyfileobj(stream, temp)
                    temp.flush()
                    os.fsync(temp.fileno())
                except BaseException:
                    temporary.unlink(missing_ok=True)
                    raise
            try:
                os.replace(temporary, target)
            finally:
                temporary.unlink(missing_ok=True)
    return len(records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, help='Use an already downloaded data ZIP')
    parser.add_argument('--destination', type=Path, default=ROOT, help='Source checkout to populate')
    parser.add_argument('--force', action='store_true', help='Replace locally modified data files')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'release-manifest.json').read_text())
    args.destination.mkdir(parents=True, exist_ok=True)
    if args.archive:
        count = restore(args.archive, args.destination, manifest, args.force)
    else:
        asset = manifest['data_archive']
        print(f"Downloading {asset['name']} ({asset['bytes'] / 1024**2:.1f} MiB)", flush=True)
        with tempfile.TemporaryDirectory(prefix='lunar-data-') as directory:
            archive = Path(directory) / asset['name']
            request = urllib.request.Request(asset['url'], headers={'User-Agent': 'LunarTerrain-data/1.5.0'})
            with urllib.request.urlopen(request, timeout=120) as response, archive.open('wb') as output:
                shutil.copyfileobj(response, output)
            count = restore(archive, args.destination, manifest, args.force)
    print(f'Verified {count} data files in {args.destination.resolve()}')


if __name__ == '__main__':
    main()
