from results.rank import matrix_rank
from results.similarity import build_similarity_matrix
from results.pca import center_matrix, compute_covariance, compute_eigen, explained_variance, project_data
import numpy as np

A = np.array([
    [1, 1, 1, 0, 0],
    [0, 1, 2, 0, 0],
    [0, 0, 0, 1, 1],
    [0, 0, 0, 2, 1]
])

print("Matrix Rank:", matrix_rank(A))
S = np.array(build_similarity_matrix(A))

print("Similarity Matrix:\n", S)
print("Is Symmetric:", np.allclose(S, S.T))
print("Diagonal:", np.diag(S))

X = center_matrix(A)
C = compute_covariance(X)

eigenvalues, eigenvectors = compute_eigen(C)

variance = explained_variance(eigenvalues)
Z2 = project_data(X, eigenvectors)

print("Explained Variance:", variance)
print("Projection Matrix:\n", Z2)
print("Projection Shape:", Z2.shape)
print("Variance Total:", np.sum(variance))