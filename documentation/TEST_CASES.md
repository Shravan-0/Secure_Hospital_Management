# Test cases

| ID | Test | Expected result |
|---|---|---|
| TC01 | Verify correct password against stored hash | Accepted |
| TC02 | Verify incorrect password | Rejected |
| TC03 | Receptionist permission check for audit logs | Denied |
| TC04 | Doctor permission check for user management | Denied |
| TC05 | Valid patient details | Accepted |
| TC06 | Empty patient name or invalid age | Rejected |
| TC07 | Valid ISO date and time | Accepted |
| TC08 | Invalid date/time | Rejected |
| TC09 | Receptionist attempts service-layer medical record creation | PermissionError |
| TC10 | Doctor attempts notes for an unassigned patient | PermissionError |

Automated unit tests cover TC01–TC08. TC09–TC10 can be demonstrated manually or added as integration tests after database initialization. Record actual results when executed on the target machine.
