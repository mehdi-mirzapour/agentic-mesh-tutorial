#!/bin/bash

echo " macOS System Data Cleanup Script ⚠️"
echo "This will attempt to free space by removing caches, logs, old Xcode data, local snapshots, and temporary system files."
echo "It will NOT touch critical system files."
echo

# Function to calculate size of a directory safely
function get_size() {
    local path=$1
    if [[ -d "$path" ]] || [[ -f "$path" ]]; then
        # du -s -k output is "size path". We take the first field and strip any non-digit chars.
        local size_val=$(du -s -k "$path" 2>/dev/null | awk '{print $1}' | tr -dc '0-9')
        echo "${size_val:-0}"
    else
        echo 0
    fi
}

# Function to calculate potential space to free
function preview_size() {
    echo "Calculating potential space to free..."
    size=0

    # User Caches & Logs
    size=$((size + $(get_size ~/Library/Caches)))
    size=$((size + $(get_size ~/Library/Logs)))

    # Xcode & Simulator
    size=$((size + $(get_size ~/Library/Developer/Xcode/DerivedData)))
    size=$((size + $(get_size ~/Library/Developer/Xcode/Archives)))
    size=$((size + $(get_size ~/Library/Developer/CoreSimulator/Devices)))

    # VS Code Caches
    size=$((size + $(get_size "$HOME/Library/Application Support/Code/Cache")))
    size=$((size + $(get_size "$HOME/Library/Application Support/Code/CachedData")))

    # Trash
    size=$((size + $(get_size ~/.Trash)))

    # Sleep image (requires sudo for real size but we'll estimate if possible)
    if [ -f "/private/var/vm/sleepimage" ]; then
        # We try to get size, but since it's system-owned it might fail without sudo
        # However, it's usually several GBs.
        img_size=$(get_size /private/var/vm/sleepimage)
        size=$((size + img_size))
    fi

    # Temp system folders (requires sudo)
    # Note: sudo here will prompt the user if needed
    temp_size=$(sudo du -s -k /private/var/folders 2>/dev/null | awk '{print $1}' | tr -dc '0-9')
    size=$((size + ${temp_size:-0}))

    # Convert to MB
    echo "Estimated space to free: $((size / 1024)) MB"
}

preview_size

echo
read -p "Do you want to proceed with deletion? (y/N): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Aborted. No files were deleted."
    exit 0
fi

echo
echo "Starting cleanup…"
echo "Note: Some system-protected files (via SIP) may skip deletion."

# 1️⃣ Delete local Time Machine snapshots
echo "Deleting local Time Machine snapshots..."
tmutil listlocalsnapshots / 2>/dev/null | awk -F. '{print $4}' | while read snapshot; do
    if [[ -n "$snapshot" ]]; then
        sudo tmutil deletelocalsnapshots "$snapshot" >/dev/null 2>&1
    fi
done

# 2️⃣ Clear user caches & logs
echo "Clearing user caches and logs…"
rm -rf ~/Library/Caches/* 2>/dev/null
rm -rf ~/Library/Logs/* 2>/dev/null

# 3️⃣ Remove old Xcode derived data and archives
echo "Removing Xcode derived data and archives…"
rm -rf ~/Library/Developer/Xcode/DerivedData/* 2>/dev/null
rm -rf ~/Library/Developer/Xcode/Archives/* 2>/dev/null

# 4️⃣ Remove old CoreSimulator devices
echo "Removing old CoreSimulator devices…"
rm -rf ~/Library/Developer/CoreSimulator/Devices/* 2>/dev/null

# 5️⃣ Clear VS Code Caches
echo "Clearing VS Code caches…"
rm -rf "$HOME/Library/Application Support/Code/Cache"* 2>/dev/null
rm -rf "$HOME/Library/Application Support/Code/CachedData"* 2>/dev/null

# 6️⃣ Homebrew Cleanup
if command -v brew &> /dev/null; then
    echo "Running Homebrew cleanup…"
    brew cleanup -s >/dev/null 2>&1
fi

# 7️⃣ npm Cache Cleanup
if command -v npm &> /dev/null; then
    echo "Cleaning npm cache…"
    npm cache clean --force >/dev/null 2>&1
fi

# 8️⃣ Empty Trash
echo "Emptying Trash…"
rm -rf ~/.Trash/* 2>/dev/null

# 9️⃣ Delete sleep image
echo "Removing sleep image…"
sudo rm -f /private/var/vm/sleepimage 2>/dev/null

# 🔟 Clear temporary system folders
echo "Clearing temporary system folders..."
sudo rm -rf /private/var/folders/* 2>/dev/null

echo
echo "✅ Cleanup complete! You may want to restart your Mac for changes to take full effect."
