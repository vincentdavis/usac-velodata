from usac_velodata import USACyclingClient

if __name__ == "__main__":
    ucc = USACyclingClient(
        cache_enabled=False, cache_dir="./cache", rate_limit=True, max_retries=3, retry_delay=1, log_level="INFO"
    )
    event_list = ucc.get_events(state="CO", year=2024)
    print(event_list)

    event_details = ucc.get_event_details(permit_id="2024-13211")

    print(event_details)
