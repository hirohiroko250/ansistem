
import { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
    appId: 'com.mylesson.app',
    appName: 'MyLesson',
    webDir: 'out',
    server: {
        androidScheme: 'https'
    }
};

export default config;
