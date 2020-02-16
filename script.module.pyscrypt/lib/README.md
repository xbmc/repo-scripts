pyscrypt
========

A very simple, pure-Python implementation of the scrypt password-based key derivation function and scrypt file format libraries.

### Features


- Pure Python (no external dependancies)
- Python 2.x and 3.x support (see below for Python 3 details)

--

**The sample code in this documentation is for Python 2.x. For Python 3.x, see the Python 3 section below.**




API
===

### scrypt PBKDF hash


The scrypt algorithm is a password-based key derivation function, which takes in several parameters to adjust the difficulty and returns a string of bytes. This is useful for transforming passwords into a target length, while at the same time increaing the cost of attempting to brute-froce guess a password.

* `password` - a passowrd
* `salt` - a cryptographic salt
* `N` - general work factor
* `r` - memory cost
* `p` - computation cost (parallelization factor)
* `dkLen` - the output length (in bytes) to return


```python
import pyscrypt

hashed = pyscrypt.hash(password = "correct horse battery staple", 
                       salt = "seasalt", 
                       N = 1024, 
                       r = 1, 
                       p = 1, 
                       dkLen = 32)
print hashed.encode('hex')
```

### Write a scrypt Encrypted File

When writing a file the `N`, `r` and `p` parameters are required. The `salt` parameter is optional, and if omitted will be generated from _urandom_.

```python
import pyscrypt

with pyscrypt.ScryptFile('filename.scrypt', "password", N = 1024, r = 1, p = 1) as f:
    f.write("Hello World")
```

To write to a file-like object without the context manager, it is important to either close the ScryptFile manually or to call finalize to ensure the footer gets flushed:

```python
import pyscrypt
import StringIO

output = StringIO.StringIO()
sf = pyscrypt.ScryptFile(output, "pass123", 1024, 1, 1)
sf.write("Hello world")
sf.finalize()

output.seek(0)
encrypted = output.read()
```

### Read a scrypt Encrypted File

```python
import pyscrypt

# Read the entire contents
with pyscrypt.ScryptFile('filename.scrypt', password = "password") as f:
    print f.read()

# Iterate over each line
with pyscrypt.ScryptFile('filename.scrypt', password = "password") as f:
    for line in f:
        print line

    # Ensure the integrity of the file after completely read
    print f.valid
```



Test Harness
============

A handful of test cases are provided for both the hash algorithm and the ScryptFile library. The ScryptFile tests generate tests that can be validated against the command line utility (http://www.tarsnap.com/scrypt.html).

```python
# python tests/run-tests-hash.py
Version: 1.6.0
Test 1: pass
Test 2: pass
Test 3: pass
Test 4: pass
Test 5: pass

# python tests/run-tests-file.py 
Version: 1.6.0
Test Encrypt/Decrypt: text_length=3 result=pass valid=True
Test Encrypt/Decrypt: text_length=16 result=pass valid=True
Test Encrypt/Decrypt: text_length=127 result=pass valid=True
Test Encrypt/Decrypt: text_length=128 result=pass valid=True
Test Encrypt/Decrypt: text_length=129 result=pass valid=True
Test Encrypt/Decrypt: text_length=1500 result=pass valid=True
Created /tmp/test-10.scrypt and /tmp/test-10.txt. Check with tarsnap.
Created /tmp/test-100.scrypt and /tmp/test-100.txt. Check with tarsnap.
Created /tmp/test-1000.scrypt and /tmp/test-1000.txt. Check with tarsnap.
Test With filename: result=pass
Test Verify: filename=tests/test1.scrypt result=pass
Test Decrypt: dec('tests/test1.scrypt') == 'tests/test1.txt' result=pass valid=None
Test Decrypt: dec('tests/test1.scrypt') == 'tests/test1.txt' result=pass valid=True
Test Decrypt: dec('tests/test1.scrypt') == 'tests/test1.txt' result=pass valid=True
Test Verify: filename=tests/test2.scrypt result=pass
Test Decrypt: dec('tests/test2.scrypt') == 'tests/test2.txt' result=pass valid=None
Test Decrypt: dec('tests/test2.scrypt') == 'tests/test2.txt' result=pass valid=None
Test Decrypt: dec('tests/test2.scrypt') == 'tests/test2.txt' result=pass valid=True
```

Notice that `valid` is sometimes None. The value of `valid` can take on one of three values:
* **None** - File has not been entirely read, so the checksum cannot be verified
* **True** - The end-of-file checksum is valid
* **False** - The end-of-file checksum is invalid (some bytes in the file are corrupt)

Performance
===========

The scrypt algorithm is a CPU and memory intense algorithm, **by design**. For comparison, here are numbers based on my MacBook Air for scrypt hashing with (N = 1024, r = 1, p =1):

**CPython** (what you probably have installed)

6 hashes per second

**Pypy** (a much faster Python implementation, see [pypy.org](http://pypy.org))

250 hashes per second

**C-Wrapper** (See the FAQ below)

2364 hashes per second


Python 3
========

This library is Python 3 friendly, however, there are a few things to note.

- The parameters `password` and `salt` must be byte objects. e.g. `b"pass123"` instead of `"pass123"`.
- ScryptFile's mode must be either `rb` or `wb`. ScryptFile has two constants to help write portable code, `ScryptFile.MODE_READ` and `ScryptFile.MODE_WRITE`.

```python
import pyscrypt

# Hash
hashed = pyscrypt.hash(password = b"correct horse battery staple", 
                       salt = b"seasalt", 
                       N = 1024, 
                       r = 1, 
                       p = 1, 
                       dkLen = 256)
print hashed

# Write a file
with pyscrypt.ScryptFile('filename.scrypt', b'password', 1024, 1, 1) as f:
    f.write(b"Hello world")

# Read a file
with pyscrypt.ScryptFile('filename.scrypt', b'password') as f:
    data = f.read()
    print(data)
```

FAQ
===

**Why is this so slow?**
It is written in pure Python. It is not meant to be fast, more of a reference solution.


**How do I get one of these C wrappers you speak of?**

```python
> # Download the source
> curl -L https://github.com/forrestv/p2pool/archive/13.4.tar.gz > p2pool-13.4.tar.gz

> # Untar
> tar -xzf p2pool-13.4.tar.gz

> # Build and install
> cd p2pool-13.4/litecoin_scrypt/
> python setup.py build
> sudo python setup.py install

> python
>>> import scrypt
>>> scrypt.hash(password = "correct horse staple battery", 
                salt = "seasalt", 
                N = 1024, 
                p = 1, 
                r = 1, 
                buflen = 256)
```
    
**How do I get a question I have added?**
E-mail me at pyscrypt@ricmoo.com with any questions, suggestions, comments, et cetera.

**Can I give you my money?**
Umm... Ok? :-)

_Bitcoin_  - `1LNdGsYtZXWeiKjGba7T997qvzrWqLXLma`

