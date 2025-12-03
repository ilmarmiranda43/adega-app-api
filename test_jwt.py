from jose import jwt, JWTError

SECRET_KEY = "app-adega-miranda"  # MESMA que você usa no deps.py e auth.py
ALGORITHM = "HS256"

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJwZXJmaWxfaWQiOjEsImV4cCI6MTc2NDgwMDIzN30.sod1eRepiwaIWk5op0X8vC_Hx4oggfjpoMH6XnVEMBY"  # sem 'Bearer '

try:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    print("JWT VÁLIDO. Payload decodificado:")
    print(payload)
except JWTError as e:
    print("JWT INVÁLIDO:", repr(e))
