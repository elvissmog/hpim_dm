# IGMP timers (in seconds)
ROBUSTNESS_VARIABLE = 2
QUERY_INTERVAL = 125
QUERY_RESPONSE_INTERVAL = 10
MAX_RESPONSE_TIME_QUERY_RESPONSE_INTERVAL = QUERY_RESPONSE_INTERVAL * 10
GROUP_MEMBERSHIP_INTERVAL = ROBUSTNESS_VARIABLE * QUERY_INTERVAL + QUERY_RESPONSE_INTERVAL
OTHER_QUERIER_PRESENT_INTERVAL = ROBUSTNESS_VARIABLE * QUERY_INTERVAL + QUERY_RESPONSE_INTERVAL / 2
STARTUP_QUERY_INTERVAL = QUERY_INTERVAL / 4
STARTUP_QUERY_COUNT = ROBUSTNESS_VARIABLE
LAST_MEMBER_QUERY_INTERVAL = 1
MAX_RESPONSE_TIME_LAST_MEMBER_QUERY_INTERVAL = LAST_MEMBER_QUERY_INTERVAL * 10
LAST_MEMBER_QUERY_COUNT = ROBUSTNESS_VARIABLE
UNSOLICITED_REPORT_INTERVAL = 10
VERSION_1_ROUTER_PRESENT_TIMEOUT = 400

# IGMP msg type
MEMBERSHIP_QUERY = 0x11
VERSION_1_MEMBERSHIP_REPORT = 0x12
VERSION_2_MEMBERSHIP_REPORT = 0x16
LEAVE_GROUP = 0x17