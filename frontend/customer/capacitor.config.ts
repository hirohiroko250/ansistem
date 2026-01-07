import { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
    appId: 'com.mylesson.app',
    appName: 'MyLesson',
    webDir: 'out',
    server: {
        url: 'http://162.43.33.37:3000',
        cleartext: true
    }
};

export default config;

