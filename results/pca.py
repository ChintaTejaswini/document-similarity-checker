import numpy as np
def center_matrix(A):
    mean = np.mean(A,axis=0)
    return A-mean

def compute_covariance(X):
    n = X.shape[0]
    return (np.dot(X.T,X))/(n-1)

def compute_eigen(C):
    eigenvalues, eigenvectors = np.linalg.eigh(C)
    idx = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[idx]
    eigenvectors = eigenvectors[:,idx]
    return eigenvalues, eigenvectors

def explained_variance(eigenvalues):
    total = np.sum(eigenvalues)
    if total == 0:
        return np.zeros_like(eigenvalues)
    variance = (eigenvalues / total ) * 100
    return variance

def project_data(X,eigenvectors):
    V2 = eigenvectors[:,:2]
    Z2 = np.dot(X,V2)
    return Z2


# ----------------------------------------------------------------------------
# Large vocabularies: same eigenvalues / eigenvectors, without building the m x m matrix
# ----------------------------------------------------------------------------
def compute_eigen_dual(X):
    """Eigen-decomposition of C = X^T X / (n-1) through the small n x n matrix X X^T / (n-1).

    X X^T and X^T X share their non-zero eigenvalues, and if (lam, u) is an eigenpair of
    the n x n matrix then v = X^T u / sqrt((n-1) lam) is the matching unit eigenvector of C.
    Returns (eigenvalues of length m, largest first, padded with zeros) and an m x r matrix of
    the r eigenvectors that have a non-zero eigenvalue.
    """
    n, m = X.shape
    K = np.dot(X, X.T) / (n - 1)
    lam, U = np.linalg.eigh(K)
    idx = np.argsort(lam)[::-1]
    lam, U = lam[idx], U[:, idx]
    keep = lam > 1e-10 * max(lam[0], 1e-300)
    lam, U = lam[keep], U[:, keep]
    V = np.dot(X.T, U) / np.sqrt((n - 1) * lam)
    eigenvalues = np.zeros(m)
    eigenvalues[:len(lam)] = lam[:m]
    return eigenvalues, V
