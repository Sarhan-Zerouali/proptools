"""Nozzle flow calculations."""

import numpy as np
from scipy.optimize import fsolve
import warnings

import proptools.constants

R_univ = proptools.constants.R_univ
g = proptools.constants.g    # pylint: disable=invalid-name

def thrust_coef(p_c, p_e, gamma, p_a=None, er=None):
    """Nozzle thrust coefficient, :math:`C_F`.

    Equation 1-33a in Huzel and Huang.

    Arguments:
        p_c (scalar): Nozzle stagnation chamber pressure [units: pascal].
        p_e (scalar): Nozzle exit static pressure [units: pascal].
        gamma (scalar): Exhaust gas ratio of specific heats [units: dimensionless].
        p_a (scalar, optional): Ambient pressure [units: pascal]. If None,
            then p_a = p_e.
        er (scalar, optional): Nozzle area expansion ratio [units: dimensionless]. If None,
            then p_a = p_e.

    Returns:
        scalar: C_F [units: dimensionless].
    """
    if (p_a is None and er is not None) or (er is None and p_a is not None):
        raise ValueError('Both p_a and er must be provided.')
    C_F = (2 * gamma**2 / (gamma - 1) \
        * (2 / (gamma + 1))**((gamma + 1) / (gamma - 1)) \
        * (1 - (p_e / p_c)**((gamma - 1) / gamma))
        )**0.5
    if p_a is not None and er is not None:
        C_F += er * (p_e - p_a) / p_c
    return C_F


def c_star(gamma, m_molar, T_c):
    """Characteristic velocity, :math:`c^*`.

    Equation 1-32a in Huzel and Huang. Note that the g in Huzel is removed here,
    because Huzel uses US units while this function uses SI.

    Arguments:
        gamma (scalar): Exhaust gas ratio of specific heats [units: dimensionless].
        m_molar (scalar): Exhaust gas mean molar mass [units: kilogram mole**-1].
        T_c (scalar): Nozzle stagnation temperature [units: kelvin].

    Returns:
        scalar: The characteristic velocity [units: meter second**-1].
    """
    return (gamma * (R_univ / m_molar) * T_c)**0.5 \
        / gamma \
        / (2 / (gamma + 1))**((gamma + 1) / (2 * (gamma - 1)))


def er_from_p(p_c, p_e, gamma):
    """Find the nozzle expansion ratio from the chamber and exit pressures.
    
    Arguments:
        p_c (scalar): Nozzle stagnation chamber pressure [units: pascal].
        p_e (scalar): Nozzle exit static pressure [units: pascal].
        gamma (scalar): Exhaust gas ratio of specific heats [units: dimensionless].

    Returns:
        scalar: Expansion ratio [units: dimensionless]
    """
    # Rocket Propulsion Elements 7th Ed, Equation 3-25
    AtAe = ((gamma + 1) / 2)**(1 / (gamma - 1)) \
        * (p_e / p_c)**(1 / gamma) \
        * ((gamma + 1) / (gamma - 1)*( 1 - (p_e / p_c)**((gamma -1) / gamma)))**0.5
    er = 1/AtAe
    return er


def throat_area(m_dot, p_c, T_c, gamma, m_molar):
    """Find the nozzle throat area.

    Arguments:
        m_dot (scalar): Propellant mass flow rate [units: kilogram second**-1].
        p_c (scalar): Nozzle stagnation chamber pressure [units: pascal].
        T_c (scalar): Nozzle stagnation temperature [units: kelvin].
        gamma (scalar): Exhaust gas ratio of specific heats [units: dimensionless].
        m_molar (scalar): Exhaust gas mean molar mass [units: kilogram mole**-1].

    Returns:
        scalar: Throat area [units: meter**2].
    """
    R = R_univ / m_molar
    # Find the Throat Area require for the specified mass flow, using
    # Eocket Propulsion Equations  7th Ed, Equation 3-24
    A_t = m_dot / ( p_c * gamma \
        * (2 / (gamma + 1))**((gamma + 1) / (2*gamma - 2)) \
        / (gamma * R  * T_c)**0.5)
    return A_t


def mass_flow(A_t, p_c, T_c, gamma, m_molar):
    """Find the mass flow thorugh a (super)sonic nozzle.

    Rocket Propulsion Elements, 8th edition, equation 3-24.

    Arguments:
        A_t (scalar): Nozzle throat area [units: meter**2].
        p_c (scalar): Nozzle stagnation chamber pressure [units: pascal].
        T_c (scalar): Nozzle stagnation temperature [units: kelvin].
        gamma (scalar): Exhaust gas ratio of specific heats [units: dimensionless].
        m_molar (scalar): Exhaust gas mean molar mass [units: kilogram mole**-1].

    Returns:
        scalar: Mass flow rate :math:`\dot{m}` [units: kilogram second**-1].
    """
    return (A_t * p_c * gamma / (gamma * R_univ / m_molar * T_c)**0.5
            * (2 / (gamma + 1))**((gamma + 1) / (2 * (gamma - 1))))


def thrust(A_t, p_c, p_e, gamma, p_a=None, er=None):
    """Nozzle thrust force.

    Arguments:
        A_t (scalar): Nozzle throat area [units: meter**2].
        p_c (scalar): Nozzle stagnation chamber pressure [units: pascal].
        p_e (scalar): Nozzle exit static pressure [units: pascal].
        gamma (scalar): Exhaust gas ratio of specific heats [units: dimensionless].
        p_a (scalar, optional): Ambient pressure [units: pascal]. If None,
            then p_a = p_e.
        er (scalar, optional): Nozzle area expansion ratio [units: dimensionless]. If None,
            then p_a = p_e.

    Returns:
        scalar: Thrust force [units: newton].
    """
    return A_t * p_c * thrust_coef(p_c, p_e, gamma, p_a, er)


def mach_from_er(er, gamma):
    """Find the exit Mach number from the area expansion ratio.
    
    Explicit Inversion of Stodola's Area-Mach Equation
    Source: J. Majdalani and B. A. Maickie
    http://maji.utsi.edu/publications/pdf/HT02_11.pdf

    Arguments:
        er (scalar): Nozzle area expansion ratio, A_e / A_t [units: dimensionless].
        gamma (scalar): Exhaust gas ratio of specific heats [units: dimensionless].

    Returns:
        scalar: The exit Mach number [units: dimensionless].
    """    
    n = 5 # order of the aproximation
    X = np.zeros((n,))
    M = np.zeros((n,))

    e = 1/float(er) # expansion ratio
    y = gamma # ratio of specific heats
    B = (y+1)/(y-1)
    k = np.sqrt( 0.5*(y-1) )
    u = e**(1/B) / np.sqrt( 1+k**2 )
    X[0] = (u*k)**(B/(1-B))
    M[0] = X[0]

    for i in xrange(1,n):
        lamb = 1/( 2*M[i-1]**(2/B)*(B-2) + M[i-1]**2 *B**2*k**2*u**2 )
        X[i] = lamb*M[i-1]*B*( M[i-1]**(2/B) - M[i-1]**2*B*k**2*u**2 \
            + ( M[i-1]**(2+2/B)*k**2*u**2*(B**2-4*B+4) \
            - M[i-1]**2*B**2*k**2*u**4 + M[i-1]**(4/B)*(2*B-3) \
            + 2*M[i-1]**(2/B)*u**2*(2-B) )**0.5 )
        M[i] = M[i-1] + X[i]
    if abs( np.imag( M[n-1] ) ) > 1e-5:
        warnings.warn('Exit Mach Number has nonzero imaginary part!')
    Me = float(np.real(M[n-1]))
    return Me


def mach_from_pr(p_c, p_e, gamma):
    """Find the exit Mach number from the pressure ratio.

    Arugments:
        p_c (scalar): Nozzle stagnation chamber pressure [units: pascal].
        p_e (scalar): Nozzle exit static pressure [units: pascal].
        gamma (scalar): Exhaust gas ratio of specific heats [units: dimensionless].

    Returns:
        scalar: Exit Mach number [units: dimensionless].
    """
    return (2 / (gamma - 1) * ((p_e / p_c)**((1 - gamma) / gamma) -1))**0.5


def is_choked(p_c, p_e, gamma):
    """Determine whether the nozzle flow is choked.

    See https://en.wikipedia.org/wiki/Choked_flow#Choking_in_change_of_cross_section_flow

    Arguments:
        p_c (scalar): Nozzle stagnation chamber pressure [units: pascal].
        p_e (scalar): Nozzle exit static pressure [units: pascal].
        gamma (scalar): Exhaust gas ratio of specific heats [units: dimensionless].

    Returns:
        bool: True if flow is choked, false otherwise.
    """
    return p_e/p_c < (2 / (gamma + 1))**(gamma / (gamma - 1))


def mach_from_area_subsonic(area_ratio, gamma):
    """Find the Mach number as a function of area ratio for subsonic flow.

    Arguments:
        area_ratio (scalar): Area / throat area [units: dimensionless].
        gamma (scalar): Ratio of specific heats [units: dimensionless].

    Returns:
        scalar: Mach number of the flow in a passage with ``area = area_ratio * (throat area)``.
    """
    # See https://www.grc.nasa.gov/WWW/winddocs/utilities/b4wind_guide/mach.html
    P = 2 / (gamma + 1)
    Q = 1 - P
    E = 1 / Q
    R = area_ratio**2
    a = P**(1 / Q)
    r = (R - 1) / (2 * a)
    X_init = 1 / ((1 + r) + (r * (r + 2))**0.5)
    X = fsolve(
        lambda X: (P + Q * X)**E - R * X,
        X_init
        )
    return X[0]**0.5


def area_from_mach(M, gamma):
    """Find the area ratio for a given Mach number.

    Argument:
        M (scalar): Mach number.
        gamma (scalar): Ratio of specific heats [units: dimensionless].

    Returns:
        scalar: Area ratio :math:`A / A_t`.
    """
    return 1 / M * (2 / (gamma + 1) * (1 + (gamma - 1) / 2 * M**2)) \
        **((gamma + 1) / (2 * (gamma - 1)))
