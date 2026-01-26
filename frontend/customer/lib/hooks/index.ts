/**
 * React Query Hooks - 統合エクスポート
 */

// User hooks
export {
  userKeys,
  useUser,
  useUpdateProfile,
  useIsLoggedIn,
  useInvalidateUser,
} from './use-user';

// Students hooks
export {
  studentKeys,
  useStudents,
  useStudent,
  useAddStudent,
  useUpdateStudent,
  useInvalidateStudents,
  useUploadStudentPhoto,
} from './use-students';

// Schools hooks
export {
  schoolKeys,
  useSchools,
  usePublicSchools,
  useSchool,
} from './use-schools';

// Brands hooks
export {
  brandKeys,
  useBrands,
  useBrandCategories,
  useBrand,
} from './use-brands';

// Tickets hooks
export {
  ticketKeys,
  useTicketBalance,
  useTicketLogs,
  useAllTicketBalances,
} from './use-tickets';

// Session management
export { useIdleTimeout } from './use-idle-timeout';

// Biometric authentication
export {
  useBiometricAuth,
  isBiometricAvailable,
} from './use-biometric-auth';
