import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import LoginPage from './Login'

describe('LoginPage Component', () => {
  it('renders email and password input fields and submit button', () => {
    const mockOnLogin = vi.fn()
    render(<LoginPage onLogin={mockOnLogin} />)

    // Check presence of Email field
    const emailLabel = screen.getByText('Email')
    expect(emailLabel).toBeDefined()
    const emailInput = screen.getByPlaceholderText('admin@hospital.org')
    expect(emailInput).toBeDefined()
    expect(emailInput.getAttribute('type')).toBe('email')

    // Check presence of Password field
    const passwordLabel = screen.getByText('Password')
    expect(passwordLabel).toBeDefined()
    const passwordInput = screen.getByPlaceholderText('••••••••')
    expect(passwordInput).toBeDefined()
    expect(passwordInput.getAttribute('type')).toBe('password')

    // Check presence of Sign In button
    const submitButton = screen.getByRole('button', { name: 'Sign In' })
    expect(submitButton).toBeDefined()
  })
})
