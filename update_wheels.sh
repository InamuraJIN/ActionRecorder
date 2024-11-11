pip download fonttools --dest ./ActRec/wheels --only-binary=:all: --python-version=3.11 --platform=macosx_10_13_universal2
pip download fonttools --dest ./ActRec/wheels --only-binary=:all: --python-version=3.11 --platform=manylinux_2_28_x86_64
pip download fonttools --dest ./ActRec/wheels --only-binary=:all: --python-version=3.11 --platform=win_amd64

pip download brotli --dest ./ActRec/wheels --only-binary=:all: --python-version=3.11 --platform=macosx_10_13_universal2
pip download brotli --dest ./ActRec/wheels --only-binary=:all: --python-version=3.11 --platform=manylinux_2_17_x86_64
pip download brotli --dest ./ActRec/wheels --only-binary=:all: --python-version=3.11 --platform=win_amd64

# Deprecated: removed the command below if the blender version 3.6 LTS is no longer supported
pip download fonttools --dest ./ActRec/wheels --only-binary=:all: --python-version=3.10 --platform=macosx_10_13_universal2
pip download fonttools --dest ./ActRec/wheels --only-binary=:all: --python-version=3.10 --platform=manylinux_2_28_x86_64
pip download fonttools --dest ./ActRec/wheels --only-binary=:all: --python-version=3.10 --platform=win_amd64

pip download brotli --dest ./ActRec/wheels --only-binary=:all: --python-version=3.10 --platform=macosx_10_13_universal2
pip download brotli --dest ./ActRec/wheels --only-binary=:all: --python-version=3.10 --platform=manylinux1_x86_64
pip download brotli --dest ./ActRec/wheels --only-binary=:all: --python-version=3.10 --platform=win_amd64