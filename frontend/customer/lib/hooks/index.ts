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
