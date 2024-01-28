import async_rediscache

# How many people are in each leaderboard
# RedisCache[leaderboard_id, int]
leaderboard_counts = async_rediscache.RedisCache(namespace="AOC_leaderboard_counts")

# Cache of data from the AoC website
# See _helpers.fetch_leaderboard for the structure of this RedisCache
leaderboard_cache = async_rediscache.RedisCache(namespace="AOC_leaderboard_cache")

# Which leaderboard each user is in
# RedisCache[member_id, leaderboard_id]
assigned_leaderboard = async_rediscache.RedisCache(namespace="AOC_assigned_leaderboard")

# Linking Discord IDs to Advent of Code usernames
# RedisCache[member_id, aoc_username_string]
account_links = async_rediscache.RedisCache(namespace="AOC_account_links")

# Member IDs that are blocked from receiving the AoC completionist role
# RedisCache[member_id, sentinel_value]
completionist_block_list = async_rediscache.RedisCache(namespace="AOC_completionist_block_list")
