def ascii_art():
    art = """
      __    __     _                            _         
     / / /\\ \\ \\___| | ___ ___  _ __ ___   ___  | |_ ___   
     \\ \\/  \\/ / _ \\ |/ __/ _ \\| '_ ` _ \\ / _ \\ | __/ _ \\  
      \\  /\\  /  __/ | (_| (_) | | | | | |  __/ | || (_) | 
       \\/  \\/ \\___|_|\\___\\___/|_| |_| |_|\\___|  \\__\\___/  
    """
    print(art)

def get_system_info():
    # Platform and OS details
    import os
    os_name = os.name  # OS name (posix for Unix, nt for Windows)
    platform = "Windows" if os_name == "nt" else "Unix/Linux/MacOS"
    
    # System info
    cpu_count = os.cpu_count()
    
    # ASCII art banner
    ascii_art()
    print("Welcome to the System Info Display!")
    print("=" * 40)
    print(f"Operating System: {platform}")
    print(f"OS Identifier: {os_name}")
    print(f"CPU Cores Available: {cpu_count}")
    print("=" * 40)

# Run the system info display
get_system_info()
