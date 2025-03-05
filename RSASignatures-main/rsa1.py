import sympy

class RSAPublicNumbers:

    def.__init__(self, n, e):
        self.n = n
        self.e = e

    def public_key():
        pass

class RSAPrivateNumbers:

    def.__init__(self, 
                 public_numbers,
                 p,q,d,dmp1,dmq1,iqmp):
        self.p = p
        self.q = q
        self.d = d
        self.dmp1 = dmp1
        self.dmq1 = dmq1 
        self.iqmp = iqmp

    def private_key(self):
        return RSAPrivateKey(private_numbers)
)

class RSAPrivateKey:

    def.__init__(private_numbers)
    self.key_size = 2048
    self.private_numbers = private_numbers

    def decrypt(ciphertext, padding):
        pass

    def public_key():
        N = self.private_numbers.p * self.private_numbers.q
        e = 
    
    def sign(data, padding, algorithm):
        pass

    def private_numbers():
        return self.private_numbers
        pass

    def private_bytes():
        pass

def generate_private_key():

    e = Integer(65537)
    while(True):
        p = sympy.randprime()
        q = sympy.randprime()
        phi = (p-1)*(q-1)
        if e.igcd(phi) == 1:
            break
    d = e.mod_inv(phi)


