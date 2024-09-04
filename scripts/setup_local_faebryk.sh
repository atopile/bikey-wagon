#!/bin/bash

function fail() {
    echo "Error: $1"
    exit 1
}

# -----------------------------------------------------------------------------

fbranch=$1
if [ -z "$fbranch" ]; then
    fbranch="main"
fi

echo "Setting up local Faebryk from branch $fbranch"

# checks ----------------------------------------------------------------------
declare -a files=(
    "pyproject.toml"
    ".gitignore"
    "LICENSE"
    "source/main.kicad_pcb"
)
for file in "${files[@]}"
do
    if [ ! -f "$file" ]; then
        echo "File $file not found. Please run this script from the root of the project."
        exit 1
    fi
done

# check python version to be at least 3.11
pyver=$(python3 --version | cut -d' ' -f2)
major_ver=$(echo "$pyver" | cut -d'.' -f1)
minor_ver=$(echo "$pyver" | cut -d'.' -f2)
if [ "$major_ver" -lt 3 ] || ([ "$major_ver" -eq 3 ] && [ "$minor_ver" -lt 11 ]); then
    echo "Python version 3.11 or higher required."
    exit 1
fi


# check poetry
poetry --version > /dev/null
if [ $? -ne 0 ]; then
    echo "Poetry not found. Please install poetry."
    exit 1
fi

# -----------------------------------------------------------------------------

prjname=$(basename $(pwd))
root=${prjname}_project

cd .. || fail
mkdir -p $root/Apps || fail
mv $prjname $root/Apps || fail

cd $root
git clone --branch $fbranch git@github.com:faebryk/faebryk.git || fail

cd Apps/$prjname || fail
poetry add --editable ../../faebryk || fail "Failed installing faebryk"
poetry install || fail "Failed installing project"

echo "Installation successful. Enter the venv by executing:"
echo "> poetry shell"