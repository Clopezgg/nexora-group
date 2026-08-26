import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../features/auth/auth-context'
import { Button, Input, Modal } from '../design-system'
import { ApiError } from '../services/httpClient'
import { ConstructionIllustration } from './ConstructionIllustration'
import './LoginPage.css'

const loginSchema = z.object({
  email: z.string().min(1, 'Ingresa tu correo electrónico').email('Correo inválido'),
  password: z.string().min(1, 'Ingresa tu contraseña'),
  rememberMe: z.boolean(),
})

type LoginFormValues = z.infer<typeof loginSchema>

export function LoginPage() {
  const { login, isLoggingIn } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [formError, setFormError] = useState<string | null>(null)
  const [apiWaking, setApiWaking] = useState(false)
  const [forgotPasswordOpen, setForgotPasswordOpen] = useState(false)

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
        (location.state as { from?: { pathname: string } } | null)?.from?.pathname ??
        '/dashboard'
      navigate(redirectTo, { replace: true })
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setFormError('Correo o contraseña incorrectos.')
      } else if (error instanceof ApiError) {
        setFormError(`Error del servidor (${error.status}): ${error.message}`)
      } else {
        setFormError('No se pudo conectar con el servidor. Verifica tu conexión e intenta nuevamente.')
      }
    } finally {
      window.clearTimeout(wakeTimer)
      setApiWaking(false)
    }
  }

  return (
    <div className="nx-login">
      <aside className="nx-login__brand">
        <div className="nx-login__brand-inner">
          <span className="nx-login__logo">NEXORA GROUP</span>
          <h1>Gestión Empresarial y Control de Construcción</h1>
          <p>Tesorería, proyectos, abastecimiento y control de obra en un solo lugar.</p>
          <ConstructionIllustration className="nx-login__illustration" />
        </div>
      </aside>
      <main className="nx-login__panel">
        <form className="nx-login__form" onSubmit={handleSubmit(onSubmit)} noValidate>
          <h2 className="nx-login__title">Iniciar sesión</h2>
          <Input
            label="Correo electrónico"
            type="email"
            autoComplete="username"
            error={errors.email?.message}
            {...register('email')}
          />
          <Input
            label="Contraseña"
            type="password"
            autoComplete="current-password"
            error={errors.password?.message}
            {...register('password')}
          />
          <div className="nx-login__row">
            <label className="nx-login__remember">
              <input type="checkbox" {...register('rememberMe')} />
              Recordarme
            </label>
            <button
              type="button"
              className="nx-login__forgot"
              onClick={() => setForgotPasswordOpen(true)}
            >
              ¿Olvidaste tu contraseña?
            </button>
          </div>

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
      </main>

      <Modal
        open={forgotPasswordOpen}
        title="Restablecer contraseña"
        onClose={() => setForgotPasswordOpen(false)}
      >
        <p>
          El flujo de autoservicio para restablecer contraseña todavía no está disponible
          (NXR-REQ-0008, arquitectura de reseteo pendiente). Mientras tanto, contacta a un
          administrador de Nexora Group para que restablezca tu acceso.
        </p>
        <Button variant="secondary" onClick={() => setForgotPasswordOpen(false)}>
          Entendido
        </Button>
      </Modal>
    </div>
  )
}
