PERMISSIONS = {
    "Admin": {"users.manage", "patients.read", "patients.write", "appointments.read",
              "appointments.write", "records.read_all", "records.write", "logs.read", "doctors.manage"},
    "Doctor": {"patients.read_assigned", "appointments.read_assigned", "records.read_assigned", "records.write_assigned"},
    "Receptionist": {"patients.read", "patients.write", "appointments.read", "appointments.write"},
}

def allowed(role, permission):
    return permission in PERMISSIONS.get(role, set())

def require(role, permission):
    if not allowed(role, permission):
        raise PermissionError("You do not have permission to perform this action.")
