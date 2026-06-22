export interface SessionUser {
  id: string
  name: string
  email: string
  role: string
  department?: string | null
  hospital_id: string
}
