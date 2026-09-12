# Contract & Mobilization production-closure baseline

RELEASE_SHA_AT_RUN_START=`e6d214ee3af7ff4559d1d5234afaf59763f42924`
RELEASE_TREE_AT_RUN_START=`ef63c78696aac2224a2b71200b87d33c10e07fba`
CANDIDATE_BASE_SHA=`e6d214ee3af7ff4559d1d5234afaf59763f42924`
CANDIDATE_HEAD_BEFORE_CLOSURE=`470489ae404e286605c997d3142552734d6113bb`
CANDIDATE_TREE_BEFORE_CLOSURE=`2fd983258bdce52ca0043183a4badaf38b1a779b`
PATCH_FILE_COUNT=17
PATCH_SHA256=`bf14fc65621b97d06e1b83c1b77853776d739dac9a592e72b32438aef0a72836`

The final branch is based on the exact candidate head. The shared checkout,
corrupt clone, and audit clone were not mutated. No production or preproduction
system was accessed.
