# This is a fork from Cody - All credit goes to him.

# Contact Energy integration for Home Assistant
View your energy usage.

## Getting started
In your configuration.yaml file, add the following:

```
sensor:
  - platform: contact_energy
    email: joe@mama.com
    password: my-secure-password
```

## Installation
### HACS (recommended)
1. [Install HACS](https://hacs.xyz/docs/setup/download), if you did not already
2. [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=sshadmin147&repository=ha-contact-energy&category=integration)
3. Install the Contact Energy integration
4. Restart Home Assistant

### Manually
Copy all files in the custom_components/contact_energy folder to your Home Assistant folder *config/custom_components/contact_energy*.

## Known issues
None known.

## Future enhancements
Your support is welcomed.
