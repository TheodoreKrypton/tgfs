import os from 'os';


type IpFamily = 'IPv4' | 'IPv6';

const loopback = (family?: IpFamily): string => {
  return family === 'IPv4' ? '127.0.0.1' : 'fe80::1';
};

export const getIPAddress = (family: IpFamily): string[] => {
  const interfaces = os.networkInterfaces();

  const all = Object.keys(interfaces)
    .map((nic) => {
      const addresses = interfaces[nic].filter(
        (details) => details.family === family && !details.internal,
      );

      return addresses.length ? addresses[0].address : undefined;
    })
    .filter(Boolean);
  return [...all, loopback(family)];
};