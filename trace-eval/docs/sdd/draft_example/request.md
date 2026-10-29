# Change request: approvals must expire

Editorial approvals currently never expire: a page approved months ago can still be published today.
We want an approval to be valid for 30 days. After that, publishing or scheduling the page must be
refused with a clear message telling the author to request a new review, and the refusal must be
visible in the audit log. The 30 days should be a platform setting that operations can change, not a
number buried in the code. When a reviewer approves a page, the date of the approval must be recorded
so that the rule can be applied.

Requested by: content-ops. Priority: normal.
