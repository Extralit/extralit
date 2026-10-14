# The following configuration tries to limit use of numpy threading and
# possible problems with fault segmentation
# For more info, please visit https://gist.github.com/EricCousineau-TRI/8a2d1550f5fa4be4fed87d55a522dbf2
import os

os.environ.update(
    OMP_NUM_THREADS="1",
    OPENBLAS_NUM_THREADS="1",
    NUMEXPR_NUM_THREADS="1",
    MKL_NUM_THREADS="1",
)
