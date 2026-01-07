import { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
    appId: 'com.mylesson.syain',
    appName: 'MyLesson Staff',
    webDir: 'out',
    server: {
        url: 'http://162.43.33.37:3001',
        cleartext: true
    }
};

export default config;
