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
