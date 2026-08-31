import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../features/auth/auth-context'
import { Button, Input } from '../design-system'
import { ApiError } from '../services/httpClient'
import './LoginPage.css'

const loginSchema = z.object({
  email: z.string().min(1, 'Ingresa tu correo electrónico').email('Correo inválido'),
  password: z.string().min(1, 'Ingresa tu contraseña'),
  rememberMe: z.boolean(),
})

type LoginFormValues = z.infer<typeof loginSchema>

/** Login oficial NEXORA — Opción 1, moderna minimalista. Una sola tarjeta
 * centrada, misma identidad en desktop y en iPhone (una columna, safe-area,
 * completable con una mano). Sin panel hero, sin SSO no funcional, sin
 * "olvidaste tu contraseña" mientras no exista autoservicio real (§8). */
export function LoginPage() {
  const { login, isLoggingIn } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [formError, setFormError] = useState<string | null>(null)
  const [apiWaking, setApiWaking] = useState(false)
  const [showPassword, setShowPassword] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '', rememberMe: false },
  })

  const onSubmit = async (values: LoginFormValues) => {
    setFormError(null)
    setApiWaking(false)
    const wakeTimer = window.setTimeout(() => setApiWaking(true), 2500)
    try {
      await login(values)
      const redirectTo =
        (location.state as { from?: { pathname: string } } | null)?.from?.pathname ?? '/inicio'
      navigate(redirectTo, { replace: true })
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setFormError('Correo o contraseña incorrectos.')
      } else {
        // Nunca exponer 405/500/stack traces al usuario (§10). El detalle
        // técnico ya queda en logs del cliente/servidor.
        setFormError('No fue posible iniciar sesión. Intenta nuevamente en unos momentos.')
      }
    } finally {
      window.clearTimeout(wakeTimer)
      setApiWaking(false)
    }
  }

  return (
    <div className="nx-login">
      <main className="nx-login__card" aria-labelledby="nx-login-title">
        <div className="nx-login__brand">
          <span className="nx-login__brand-mark" aria-hidden="true" />
          <span className="nx-login__brand-name">NEXORA GROUP</span>
        </div>

        <div className="nx-login__head">
          <h1 id="nx-login-title" className="nx-login__title">
            Bienvenido a NEXORA
          </h1>
          <p className="nx-login__subtitle">Ingresa para continuar.</p>
        </div>

        <form className="nx-login__form" onSubmit={handleSubmit(onSubmit)} noValidate>
          <Input
            label="Correo electrónico"
            type="email"
            inputMode="email"
            autoComplete="email"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            error={errors.email?.message}
            {...register('email')}
          />

          <div className="nx-login__password">
            <Input
              label="Contraseña"
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              error={errors.password?.message}
              {...register('password')}
            />
            <button
              type="button"
              className="nx-login__password-toggle"
              onClick={() => setShowPassword((visible) => !visible)}
              aria-pressed={showPassword}
            >
              {showPassword ? 'Ocultar' : 'Mostrar'}
            </button>
          </div>

          <label className="nx-login__remember">
            <input type="checkbox" {...register('rememberMe')} />
            Recordarme
          </label>

          {apiWaking ? (
            <p className="nx-login__notice" role="status">
              El servidor está despertando, esto puede tardar unos segundos…
            </p>
          ) : null}
          {formError ? (
            <p className="nx-login__notice nx-login__notice--error" role="alert">
              {formError}
            </p>
          ) : null}

          <Button type="submit" loading={isLoggingIn} className="nx-login__submit">
            Iniciar sesión
          </Button>
        </form>

        <p className="nx-login__footer">Acceso seguro · Sesiones auditadas · Trazabilidad completa</p>
      </main>
    </div>
  )
}
