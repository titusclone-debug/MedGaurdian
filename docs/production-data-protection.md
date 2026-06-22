# Production Data Protection

## Patient-identifying fields

The current consent schema still contains plaintext patient name, mobile number,
address, and digital signature fields. Real patient data must not be enabled in
production until the encryption migration below is completed.

The approved implementation direction is application-level envelope encryption
with a key held in the deployment secret manager or managed KMS. A Fernet key
can be generated for development with:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Before real patient data is accepted, operators must:

1. complete the one-time Alembic adoption,
2. widen encrypted string columns through a reviewed migration,
3. configure and escrow the encryption key,
4. back up the database,
5. encrypt legacy plaintext patient fields,
6. verify decryptability,
7. establish key rotation and break-glass recovery procedures.

## Retention

Retention periods must be approved by legal, clinical governance, and privacy
officers. Code must not invent retention or deletion policy. Evidence, approval,
consent, and audit records require separate approved schedules and legal holds.
