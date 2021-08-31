import argparse
import re
from typing import Optional
from typing import Sequence

from cfgv import apply_defaults

import pre_commit.constants as C
from pre_commit import git
from pre_commit.clientlib import load_config
from pre_commit.clientlib import MANIFEST_HOOK_DICT
from pre_commit.commands.run import Classifier


def exclude_matches_any(
        filenames: Sequence[str],
        include: str,
        exclude: str,
) -> bool:
    if exclude == '^$':
        return True
    include_re, exclude_re = re.compile(include), re.compile(exclude)
    for filename in filenames:
        if include_re.search(filename) and exclude_re.search(filename):
            return True
    return False


def check_useless_excludes(config_file: str) -> int:
    config = load_config(config_file)
    filenames = git.get_all_files()
    classifier = Classifier.from_config(
        filenames, config['files'], config['exclude'],
    )
    retv = 0

    exclude = config['exclude']
    if not exclude_matches_any(filenames, '', exclude):
        print(
            f'The global exclude pattern {exclude!r} does not match any files',
        )
        retv = 1

    for repo in config['repos']:
        for hook in repo['hooks']:
            # the default of manifest hooks is `types: [file]` but we may
            # be configuring a symlink hook while there's a broken symlink
            hook.setdefault('types', [])
            # Not actually a manifest dict, but this more accurately reflects
            # the defaults applied during runtime
            hook = apply_defaults(hook, MANIFEST_HOOK_DICT)
            names = classifier.filenames
            types = hook['types']
            types_or = hook['types_or']
            exclude_types = hook['exclude_types']
            names = classifier.by_types(names, types, types_or, exclude_types)
            include, exclude = hook['files'], hook['exclude']
            if not exclude_matches_any(names, include, exclude):
                print(
                    f'The exclude pattern {exclude!r} for {hook["id"]} does '
                    f'not match any files',
                )
                retv = 1

    return retv


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('filenames', nargs='*', default=[C.CONFIG_FILE])
    args = parser.parse_args(argv)

    retv = 0
    for filename in args.filenames:
        retv |= check_useless_excludes(filename)
    return retv


if __name__ == '__main__':
    exit(main())
