def format_speed(Bps: float) -> str:
    """Formats speed from Bytes/sec to a readable string (kbps/Mbps)."""
    # Handle invalid or negative inputs gracefully.
    if not isinstance(Bps, (int, float)) or Bps < 0:
        return "0.0 kbps"
        
    if Bps < 125000:  # Under 1 Mbps (125,000 Bytes/sec)
        return f"{Bps * 8 / 1000:.1f} kbps"
    else:
        return f"{Bps * 8 / 1000000:.2f} Mbps"