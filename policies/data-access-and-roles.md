---
id: data-access-and-roles
title: Who May See Which Data
owner: Information Security, with Compliance
version: 3.2
effective: 2026-04-01
applies_to: [all_staff]
---

# Who May See Which Data

> Synthetic document written for the Secure Multi-Agent Delegation project. The bank, its rules and its numbers are invented. Not a real bank's policy and not legal or regulatory advice.

## Principle

Staff see the data their job needs and nothing more. Access is enforced by the bank's systems as the logged-in
person; a tool, report or assistant used by a member of staff sees only what that person could see.

## Access by role

| Role | Customers, accounts, transactions | Loans | Employees and salaries |
| --- | --- | --- | --- |
| Teller | Own branch only | None | None |
| Branch Manager | Own branch only | Own branch only | Own branch only |
| HR | None | None | All branches |
| Internal Auditor | All branches; national ID, phone and full account numbers hidden (masked forms only) | All branches | All branches; phone hidden |
| Data Intern | Aggregate figures only, with groups of fewer than 5 suppressed | Aggregate only | Aggregate headcount only |

Branch details (names, codes, cities) are visible to everyone.

## Requests for more access

Extra access is requested through Information Security with the manager's approval and a business reason, and is
time-limited. Using another person's login, or asking a colleague to run a query you could not run yourself, is a
breach.

## Related

pii-masking-and-bulk-export, customer-data-sharing, ai-assistant-use.
