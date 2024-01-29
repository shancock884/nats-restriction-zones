# NATS Restriction Zones

This project contains a script to autogenerate the "ENR 5.1 Prohibited, restricted and danger areas"
section of airspace.yaml for the data in: https://github.com/ahsparrow/airspace.

## Source

The source data is provided in AIXM format on the NATS website here:
https://nats-uk.ead-it.com/cms-nats/opencms/en/uas-restriction-zones/

## Running

To run the script use:
```
./nats_restriction_zones <AIXM file>
```
The output will be a YAML file of the same base name, which can be pasted into airspace.yaml to replace
the previous section.
