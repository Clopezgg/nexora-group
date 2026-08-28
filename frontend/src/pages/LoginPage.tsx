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
        '/inicio'
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
      <section className="nx-login__hero">
        <div className="nx-login__hero-inner">
          <div className="nx-login__brand-lockup">
            <span className="nx-login__brand-mark" aria-hidden="true" />
            <div>
              <strong>NEXORA</strong>
              <span>Gestión Financiera para Construcción</span>
            </div>
          </div>
          <div className="nx-login__hero-copy">
            <p className="nx-login__kicker">CONTROL EMPRESARIAL · TESORERÍA · PROYECTOS</p>
            <h1>Control total. Claridad financiera. Construcción con confianza.</h1>
            <p>
              Una sola plataforma para tesorería central, operaciones, proyectos,
              abastecimiento, comercial y auditoría.
            </p>
          </div>
          <ConstructionIllustration className="nx-login__illustration" />
          <div className="nx-login__scope-strip" aria-label="Alcances de operación">
            <span><b>CENTRAL</b>Tesorería y movimientos internos</span>
            <span><b>GENERAL</b>Operación sin proyecto</span>
            <span><b>PROYECTO</b>Control financiero de obra</span>
          </div>
        </div>
      </section>

      <main className="nx-login__panel">
        <div className="nx-login__panel-inner">
          <form className="nx-login__form" onSubmit={handleSubmit(onSubmit)} noValidate>
            <div className="nx-login__form-head">
              <span className="nx-login__form-badge">NEXORA GROUP</span>
              <h2 className="nx-login__title">Iniciar sesión</h2>
              <p>Accede a tu cuenta para continuar.</p>
            </div>
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
            <div className="nx-login__secure-note">Acceso seguro · Sesiones auditadas · Trazabilidad completa</div>
          </form>

          <div className="nx-login__trust-strip" aria-label="Características de seguridad">
            <span><b>Seguro</b>Sesiones protegidas</span>
            <span><b>Confiable</b>Operación centralizada</span>
            <span><b>Auditado</b>Trazabilidad completa</span>
            <span><b>En la nube</b>Acceso desde cualquier lugar</span>
          </div>
        </div>
      </main>

      <Modal
        open={forgotPasswordOpen}
        title="Restablecer contraseña"
        onClose={() => setForgotPasswordOpen(false)}
      >
        <p>
          El restablecimiento de contraseña por autoservicio no está habilitado en esta instancia.
          Solicita a un administrador de Nexora Group el restablecimiento de tu acceso.
        </p>
        <Button variant="secondary" onClick={() => setForgotPasswordOpen(false)}>
          Entendido
        </Button>
      </Modal>
    </div>
  )
}
