import sys
sys.path.insert(0, ".")
import config
import data_loader
import matcher
import schemas
print("config: OK")
data_loader.load_all()
g = data_loader.get_grants()
s = data_loader.get_startups_df()
print("data_loader: OK -", len(g), "grants,", len(s), "startups")
matches = matcher.match_grants_for_startup(startup_id="ST014", min_score=0.2, max_results=5)
print("matcher: OK -", len(matches), "matches for ST014")
for m in matches[:3]:
    print(" ", m["grant_id"], m["grant_name"][:40], "score=" + str(m["match_score"]))
stats = matcher.get_statistics()
print("total_grants:", stats["total_grants"])
print("total_max_funding_inr:", stats["total_max_funding_inr"])

# Validate schemas by importing
from schemas import MatchRequest, MatchResponse, ProposalRequest, EligibilityRequest
print("schemas: OK")

# Validate mock proposal gen
import os
os.environ["PROPOSAL_BACKEND"] = "mock"
import importlib
import granite_client
importlib.reload(granite_client)
startup = data_loader.get_startup_by_id("ST014")
grant = data_loader.get_grant_by_id("GR002")
proposal = granite_client.generate_proposal(startup, grant)
print("granite_client mock proposal: OK, length=", len(proposal))
elig = granite_client.generate_eligibility_analysis(startup, grant)
print("granite_client mock eligibility: OK, length=", len(elig))
summary = granite_client.generate_grant_summary(grant)
print("granite_client mock summary: OK, length=", len(summary))

print()
print("=== ALL MODULES VALIDATED SUCCESSFULLY ===")
