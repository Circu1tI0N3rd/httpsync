#!/usr/bin/env python3

def indepthDictUpdate(A, B):
    if type(B) is dict and type(A) is dict:
        for key in B.keys():
            if key in A:
                if type(A[key]) is list and type(B[key]) is list:
                    A[key] += B[key]
                elif type(A[key]) is dict and type(B[key]) is dict:
                    indepthDictUpdate(A[key], B[key])
                elif type(A[key]) is dict:
                    A[key].update(B[key])
                else:
                    A[key] = B[key]
            else:
                A[key] = B[key]

def transverseDict(tree, keys):
    if tree is None:
        return None
    dest = tree
    for key in keys:
        if key in dest:
            dest = dest[key]
        else:
            return None
    return dest

def filesTree(tree, path = []):
    lst = []
    if tree is not None:
        for key in tree.keys():
            if key == 'files':
                lst.append(tuple(path + [key]))
            else:
                lst += filesTree(tree[key], path + [key])
    return lst

def listStat(index):
    count = 0
    filesPath = filesTree(index)
    for path in filesPath:
        count += len(transverseDict(index, path))
    return count
