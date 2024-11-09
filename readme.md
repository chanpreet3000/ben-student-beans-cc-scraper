# StudentBeans Discord Bot

A Discord bot that automatically scrapes and manages Superdrug coupon codes from StudentBeans.com. The bot uses 100 different credentials to fetch codes and distributes them to users through Discord channels.

## What is this bot?

This Discord bot automates the process of:
1. Scraping Superdrug coupon codes from StudentBeans.com using 100 different credentials
2. Storing them in a MongoDB database
3. Distributing them to users via Discord
4. Managing notification channels for updates

The bot runs periodic checks every 24 hours to maintain a fresh supply of coupon codes and notifies designated channels about stock updates.

## Discord Commands

Here's a detailed breakdown of all available commands and their functionality:

### `/sb-add-channel #channel`
Adds a Discord channel to receive notifications about coupon code updates.
- Required Permission: Administrator
- How it works: The bot stores the channel ID in the database and will send all future notifications to this channel
- Response: Confirms if the channel was added or if it was already in the notification list

### `/sb-remove-channel #channel`
Removes a Discord channel from the notification list.
- Required Permission: Administrator
- How it works: The bot removes the channel ID from the database and stops sending notifications to this channel
- Response: Confirms if the channel was removed or if it wasn't in the notification list

### `/sb-list-channels`
Shows all channels currently set up to receive notifications.
- Required Permission: None
- How it works: The bot fetches all channel IDs from the database and displays them as a list
- Response: Shows a list of all channels with their mentions, or indicates if no channels are configured

### `/sb-get-unused-coupon-codes [total_codes]`
Retrieves a specified number of unused coupon codes.
- Required Permission: None
- How it works: 
  1. The bot fetches the requested number of oldest unused codes from the database
  2. Sends the codes via DM to maintain privacy
  3. Marks these codes as used to prevent future distribution
- Response: Confirms that the codes were sent via DM, or indicates if no unused codes are available

### `/sb-coupon-codes-count`
Shows the current count of available unused coupon codes.
- Required Permission: None
- How it works: The bot queries the database to count all coupon codes marked as unused
- Response: Displays the total number of unused coupon codes currently available

## Automatic Features

The bot includes an automated system that:
- Runs checks every 24 hours for new coupon codes
- Uses 100 different credentials to maximize code collection
- Updates all notification channels about the current stock
- Maintains the database of unused codes
- Ensures codes aren't distributed multiple times

## License

MIT License