import numpy as np

def matrix_rank(A):
    matrix = np.array(A,dtype=float)
    rank = np.linalg.matrix_rank(matrix)
    return rank

# calculates rank through linear algebra module in numpy