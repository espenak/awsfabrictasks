#!/bin/bash

# Bash completion for "bin/awsfab".
# If you have awsfab on your PATH, you probably want to use
# awsfab_completion.bash instead, to autocomplete "awsfab".

function _awsfab_completion()
{
    command=$1
    _fab_commands=$($command --shortlist)
    local cur prev
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    COMPREPLY=( $(compgen -W "${_fab_commands}" -- ${cur}) )
    return 0
}
complete -o nospace -F _awsfab_completion bin/awsfab
