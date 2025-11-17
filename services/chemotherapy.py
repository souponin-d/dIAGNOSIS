import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from sklearn.metrics import mean_squared_error, root_mean_squared_error, mean_absolute_error

# *** Подготовка данных ***************************************************************************

full_data = []

for i in range(1,5):
    full_data.append(pd.read_excel(r'Downloads/breast_cancer_data.xlsx',sheet_name=f'Стадия {i}'))

full_data = pd.concat(full_data, ignore_index=True)

# *** Определение параметров роста без лечения(BASE LINE) ******************************************

def logistic_model(t, a, K, V0):
    return K * V0 / (V0 + (K - V0) * np.exp(-a * t))

a_hat_arr = []

plt.figure(figsize=(10,6))

t_data = np.array([0., 3., 6., 12., 24.])

for stage in [1,2,3,4]:

    subset = full_data[(full_data['treatment'] == 'no_treatment') & (full_data['stage'] == stage)]

    if len(subset)==0:
        print(f"Нет пациентов для данной стадии{stage}")
        a_hat_arr.append(np.nan)
        continue

    K = subset.iloc[:,14:19].to_numpy().max() * 1.5

    a_individual = []

    for idx, row in subset.iterrows():
        V_data = row.iloc[14:19].values.astype(float)
        V0 = V_data[0]
        t_rel = t_data - t_data[0]

        try:
            popt, _ = curve_fit(
                lambda t, a: logistic_model(t, a, K, V0),
                t_rel, V_data,
                p0=[0.1],
                bounds=(0, np.inf)
            )
            a_individual.append(popt[0])
        except:
            continue

    a_hat = np.mean(a_individual)
    a_hat_arr.append(a_hat)

    print(f"Стадия {stage}: a = {a_hat}")

    mean_values = subset.iloc[:,14:19].mean(axis=0).values
    V0 = mean_values[0]
    t_rel = t_data - t_data[0]
    t_fine = np.linspace(0,24,200)
    V_fit = logistic_model(t_fine, a_hat, K, V0)

    plt.scatter(t_data, mean_values, label=f"Стадия {stage} Стадия")
    plt.plot(t_fine, V_fit, label=f"Стадия {stage} зафиченая")

plt.legend()
plt.xlabel("Месяцы")
plt.ylabel("Размер опухоли")
plt.title("Скорость роста подобрпнная под стадии")
plt.grid(True)
plt.show()

print("Конечный набор скоростей для каждой стадии a_hat_arr:", a_hat_arr)

# *** Отчистка данных и выбор только лечение химиотерапией *****************************************

clear_data = full_data[(full_data["treatment_response"] != "progression") & (full_data["treatment"] == "surgery_chemo")]
clear_data

# *** Моделируем сразу четыре стадии опухоли *******************************************************

# ===== 1. Исходные данные =====

all_stage_metrics = []

tumor_values_all = clear_data.iloc[:, 14:19].astype(float)

t_data = np.array([0., 3., 6., 12., 24.])

group_col = "stage"
groups = clear_data[group_col].unique()

K_arr = np.max(tumor_values_all) * 1.0 
dt = 0.01

# ===== 2. Трёхкомпартментная модель S–T–R =====

def simulate_three_compartments(t_end,
                                beta_kill, gamma,
                                r, K, V0,
                                alpha=0.02,   
                                beta_back=0.01,
                                mu=0.02,    
                                sense_S=1.0,   
                                sense_T=0.3,  
                                sense_R=0.0,    
                                dt=0.01):
    """ Трехкомпартментная модель для трех типов клеток внутри опухолевой популяции

    Определение основных параметров для модели: 

    betta_kill - базовая сила противоопухолевого препарата 
    gamma - скорость затухания эффекта препарата во времени
    r - скорость пролиферативной активности клеток опухоли
    K - емкость среды(максималбно возможный объем среды)
    V0 - начальный общий объем опухоли

    alpha - скорость перехода клеток S в T
    betta_back - скорость перехода из T в S
    mu - скорость перехода из T в R

    sense_S - чувствительность клеток S к препарату 
    sense_T - чувствительность клеток T к препарату 
    sense_R - чувствительность клеток R к препарату 
    """
    T = np.arange(0, t_end + dt, dt)

    S = np.zeros_like(T, dtype=float)
    TOL = np.zeros_like(T, dtype=float)
    R = np.zeros_like(T, dtype=float)
    Ntot = np.zeros_like(T, dtype=float)

    S[0] = V0 * 0.95
    TOL[0] = V0 * 0.0
    R[0] = V0 * 0.05
    Ntot[0] = S[0] + TOL[0] + R[0]

    for i in range(1, len(T)):
        t = T[i]
        kill = beta_kill * np.exp(-gamma * t)
        N_prev = Ntot[i-1]

        dS = r * S[i-1] * (1 - N_prev / K) - kill*S[i-1] * sense_S - alpha*S[i-1] + beta_back*TOL[i-1]
        dT = alpha*S[i-1] - beta_back*TOL[i-1] - mu*TOL[i-1] - kill*T[i-1] * sense_T
        dR = r * R[i-1] * (1 - N_prev / K) + mu*TOL[i-1] - kill*R[i-1] * sense_R

        S[i] = S[i-1] + dS*dt
        TOL[i] = TOL[i-1] + dT*dt
        R[i] = R[i-1] + dR*dt

        Ntot[i] = S[i] + TOL[i] + R[i]

    return T, S, TOL, R, Ntot

r = a_hat_arr[0]
def model_for_fit(t_points, beta_kill, gamma, alpha, mu, r=r, K=K_arr, V0=V0):
    t_end = t_points.max()
    T, S, TOL, R, Ntot = simulate_three_compartments(
        t_end,
        beta_kill, gamma,
        r, K, V0,
        alpha=alpha,
        mu=mu,
        dt=dt
    )
    return np.interp(t_points, T, Ntot)


fit_results = {}

for idx, g in enumerate(groups):
    print(f"\n===== Stage {g} =====")

    mask = clear_data[group_col] == g

    tumor_values = tumor_values_all.loc[mask, :]

    if tumor_values.empty:
        print(f"Stage {g}: нет данных по опухоли, пропускаю.")
        continue

    V_data = tumor_values.mean(axis=0).values
    V0 = float(V_data[0])
    print("V0 =", V0)

    r_stage = a_hat_arr[idx] 

    def model_for_fit_group(t_points, beta_kill, gamma, alpha, mu,
                            r=r_stage, K=K_arr, V0=V0):
        return model_for_fit(t_points, beta_kill, gamma, alpha, mu, r=r, K=K, V0=V0)

    p0 = [0.5, 0.1, 0.02, 0.02]
    bounds = ([0, 0, 0, 0], [15, 10, 1.0, 1.0])

    popt, pcov = curve_fit(
        model_for_fit_group,
        t_data,
        V_data,
        p0=p0,
        bounds=bounds,
        maxfev=20000
    )

    beta_kill_fit, gamma_fit, alpha_fit, mu_fit = popt

    fit_results[g] = {
        'beta': beta_kill_fit,
        'gamma': gamma_fit,
        'alpha': alpha_fit,
        'mu': mu_fit,
        'V_data': V_data,
        'V0': V0
    }

    print(f" beta_kill={beta_kill_fit:.4f}, gamma={gamma_fit:.4f}, alpha={alpha_fit:.4f}, mu={mu_fit:.4f}")



# ===== 3. Визуализация =====
plt.figure(figsize=(10, 6))
colors = plt.cm.tab10(np.linspace(0, 1, len(groups)))

for color, g in zip(colors, groups):
    res = fit_results[g]

    beta_kill = res['beta']
    gamma = res['gamma']
    alpha = res['alpha']
    mu = res['mu']
    V0 = res['V0']
    V_data = res['V_data']

    r_stage = a_hat_arr[g-1]

    T_dense, S_dense, TOL_dense, R_dense, Ntot_dense = simulate_three_compartments(
            t_end=t_data.max(),
            beta_kill=beta_kill,
            gamma=gamma,
            r=r_stage,
            K=K_arr,
            V0=V0,
            alpha=alpha,
            mu=mu,
            dt=dt
        )
    
    metrics_data = clear_data[clear_data['stage'] == g].iloc[:, 14:19]

    y_true = np.mean(metrics_data, axis=0)
    y_pred = np.interp(t_data, T_dense, Ntot_dense)

    rmse = root_mean_squared_error(y_true, y_pred)
    mse = mean_squared_error(y_true, y_pred)
    mae = mean_absolute_error(y_true, y_pred)
    nrmse = rmse * 100 / (y_true.max() - y_true.min())

    all_stage_metrics.append({
    'stage': g,
    'mse': mse,
    'mae': mae,
    'rmse': rmse,
    'nrmse %': nrmse
            })

    plt.plot(T_dense, Ntot_dense, color=color, label=f"{g} — total", linewidth=2)
    plt.plot(T_dense, S_dense, '--', color=color, alpha=0.6, label=f"{g} — S")
    plt.plot(T_dense, TOL_dense, ':', color=color, alpha=0.8, label=f"{g} — T")
    plt.plot(T_dense, R_dense, '-.', color=color, alpha=0.8, label=f"{g} — R")

    plt.scatter(t_data, V_data, color=color, edgecolor="k", zorder=3)

plt.title("S–T–R модель опухоли")
plt.xlabel("Месяцы")
plt.ylabel("Объём опухоли")
plt.grid(alpha=0.3)
plt.legend(fontsize=7)
plt.tight_layout()
plt.show()

stage_metrics = pd.DataFrame(all_stage_metrics)
stage_metrics

# *** Моделируем отедльно четвертую стадию (для удобства визуализации логики) *******************************************************

# ===== 0. Метрики ======
all_stage_metrics = []

# ===== 1. Исходные данные =====
tumor_values_all = clear_data.iloc[:, 14:19].astype(float)

t_data = np.array([0., 3., 6., 12., 24.])

group_col = "stage"
groups = clear_data[group_col].unique()

K_arr = np.max(tumor_values_all) * 1.0  
dt = 0.01

# ===== 2. Трёхкомпартментная модель S–T–R =====
def simulate_three_compartments(t_end,
                                beta_kill, gamma,
                                r, K, V0,
                                alpha=0.02,   
                                beta_back=0.01,
                                mu=0.02,         
                                sense_S=1.0,      
                                sense_T=0.3,        
                                sense_R=0.0,    
                                dt=0.01):

    T = np.arange(0, t_end + dt, dt)

    S = np.zeros_like(T, dtype=float)
    TOL = np.zeros_like(T, dtype=float)
    R = np.zeros_like(T, dtype=float)
    Ntot = np.zeros_like(T, dtype=float)

    S[0] = V0 * 0.95
    TOL[0] = V0 * 0.0
    R[0] = V0 * 0.05
    Ntot[0] = S[0] + TOL[0] + R[0]

    for i in range(1, len(T)):
        t = T[i]
        kill = beta_kill * np.exp(-gamma * t)
        N_prev = Ntot[i-1]

        dS = r * S[i-1] * (1 - N_prev / K) - kill*S[i-1] * sense_S - alpha*S[i-1] + beta_back*TOL[i-1]
        dT = alpha*S[i-1] - beta_back*TOL[i-1] - mu*TOL[i-1] - kill*T[i-1] * sense_T
        dR = r * R[i-1] * (1 - N_prev / K) + mu*TOL[i-1] - kill*R[i-1] * sense_R

        S[i] = S[i-1] + dS*dt
        TOL[i] = TOL[i-1] + dT*dt
        R[i] = R[i-1] + dR*dt

        Ntot[i] = S[i] + TOL[i] + R[i]

    return T, S, TOL, R, Ntot


# === Трёхкомпартментная модель S–T–R, с добавлением начала в новой точке при неэффективном лечении ===
def simulate_three_compartments_segment(t_start,
                                        t_end,
                                        beta_kill, gamma,
                                        r, K,
                                        S0, T0, R0,
                                        alpha=0.02,
                                        beta_back=0.01,
                                        sense_S=0.6,  
                                        sense_T=0.1,    
                                        sense_R=0.1,
                                        mu=0.02,
                                        dt=0.01):

    T = np.arange(t_start, t_end + dt, dt)

    S = np.zeros_like(T, dtype=float)
    TOL = np.zeros_like(T, dtype=float)
    R = np.zeros_like(T, dtype=float)
    Ntot = np.zeros_like(T, dtype=float)

    S[0]   = S0
    TOL[0] = T0
    R[0]   = R0
    Ntot[0] = S0 + T0 + R0

    for i in range(1, len(T)):
        t = T[i]
        tau = t - t_start
        kill = beta_kill * np.exp(-gamma * tau)
        N_prev = Ntot[i-1]


        dS = r * S[i-1] * (1 - N_prev / K) - kill*S[i-1] * sense_S - alpha*S[i-1] + beta_back*TOL[i-1]
        dT = alpha*S[i-1] - beta_back*TOL[i-1] - mu*TOL[i-1] - kill*T[i-1] * sense_T
        dR = r * R[i-1] * (1 - N_prev / K) + mu*TOL[i-1] - kill*R[i-1] * sense_R

        S[i]   = S[i-1] + dS*dt
        TOL[i] = TOL[i-1] + dT*dt
        R[i]   = R[i-1] + dR*dt

        Ntot[i] = S[i] + TOL[i] + R[i]

    return T, S, TOL, R, Ntot

def model_for_fit(t_points, beta_kill, gamma, alpha, mu, r=r, K=K_arr, V0=V0):
    t_end = t_points.max()
    T, S, TOL, R, Ntot = simulate_three_compartments(
        t_end,
        beta_kill, gamma,
        r, K, V0,
        alpha=alpha,
        mu=mu,
        dt=dt
    )
    return np.interp(t_points, T, Ntot)


fit_results = {}

g = 4

mask = clear_data[group_col] == g

tumor_values = tumor_values_all.loc[mask, :]

V_data = tumor_values.mean(axis=0).values
V0 = float(V_data[0])

r_stage = a_hat_arr[g-1]

def model_for_fit_group(t_points, beta_kill, gamma, alpha, mu,
                        r=r_stage, K=K_arr, V0=V0):
    return model_for_fit(t_points, beta_kill, gamma, alpha, mu, r=r, K=K, V0=V0)

p0 = [0.5, 0.1, 0.02, 0.02]
bounds = ([0, 0, 0, 0], [15, 10, 1.0, 1.0])

popt, pcov = curve_fit(
    model_for_fit_group,
    t_data,
    V_data,
    p0=p0,
    bounds=bounds,
    maxfev=20000
)

beta_kill_fit, gamma_fit, alpha_fit, mu_fit = popt

fit_results[g] = {
    'beta': beta_kill_fit,
    'gamma': gamma_fit,
    'alpha': alpha_fit,
    'mu': mu_fit,
    'V_data': V_data,
    'V0': V0
}

print(f" beta_kill={beta_kill_fit:.4f}, gamma={gamma_fit:.4f}, alpha={alpha_fit:.4f}, mu={mu_fit:.4f}")

# ===== 3. Базовая кривая без смены терапии =====
plt.figure(figsize=(10, 6))

res = fit_results[g]

beta_kill = res['beta']
gamma     = res['gamma']
alpha     = res['alpha']
mu        = res['mu']
V0        = res['V0']
V_data    = res['V_data']

r_stage = a_hat_arr[g-1]

T_dense, S_dense, TOL_dense, R_dense, Ntot_dense = simulate_three_compartments(
        t_end=t_data.max(),
        beta_kill=beta_kill,
        gamma=gamma,
        r=r_stage,
        K=K_arr,
        V0=V0,
        alpha=alpha,
        mu=mu,
        dt=dt
    )

metrics_data = clear_data[clear_data['stage'] == g].iloc[:, 14:19]

y_true = np.mean(metrics_data, axis=0)
y_pred = np.interp(t_data, T_dense, Ntot_dense)

rmse = root_mean_squared_error(y_true, y_pred)
mse  = mean_squared_error(y_true, y_pred)
mae  = mean_absolute_error(y_true, y_pred)
nrmse = rmse * 100 / (y_true.max() - y_true.min())

all_stage_metrics.append({
    'stage': g,
    'mse': mse,
    'mae': mae,
    'rmse': rmse,
    'nrmse %': nrmse, 
    'beta_kill': beta_kill_fit,
    'gamma': gamma_fit,
    'alpha': alpha_fit,
    'mu': mu_fit
})

idx_min = np.argmin(Ntot_dense)  
t_min = float(T_dense[idx_min])
plt.axvline(t_min, linestyle='--', color='red')
print("t_min =", t_min)

plt.plot(T_dense, Ntot_dense, label=f"{g} — total (без смены)", linewidth=2)
plt.plot(T_dense, S_dense,   '--', label=f"{g} — Чувствительные")
plt.plot(T_dense, TOL_dense, ':', label=f"{g} — Толерантные")
plt.plot(T_dense, R_dense,   '-.', label=f"{g} — Резистентные")
plt.scatter(t_data, V_data, edgecolor="k", zorder=3)

# ===== 4. Сценарий со сменой терапии после t_min =====

S_min   = S_dense[idx_min]
TOL_min = TOL_dense[idx_min]
R_min   = R_dense[idx_min]

beta_kill_new = beta_kill * 4
gamma_new     = gamma * 2

T_sw, S_sw, TOL_sw, R_sw, N_sw = simulate_three_compartments_segment(
    t_start=t_min,
    t_end=t_data.max(),
    beta_kill=beta_kill_new,
    gamma=gamma_new,
    r=r_stage,
    K=K_arr,
    S0=S_min,
    T0=TOL_min,
    R0=R_min,
    alpha=alpha,
    beta_back=0.01,
    mu=mu,
    dt=dt
)

def clip_to_zero(arr):
    arr[arr < 0] = 0
    return arr

S_sw = np.clip(S_sw, 0, None)
TOL_sw = np.clip(TOL_sw, 0, None)
R_sw = np.clip(R_sw, 0, None)
N_sw = np.clip(N_sw, 0, None)

S_sw  = np.clip(S_sw,  0, None)
TOL_sw = np.clip(TOL_sw, 0, None)
R_sw  = np.clip(R_sw,  0, None)
N_sw  = np.clip(N_sw,  0, None)

T_before   = T_dense[:idx_min+1]
N_before   = Ntot_dense[:idx_min+1]
S_before   = S_dense[:idx_min+1]
TOL_before = TOL_dense[:idx_min+1]
R_before   = R_dense[:idx_min+1]

T_full   = np.concatenate([T_before,   T_sw[1:]])
N_full   = np.concatenate([N_before,   N_sw[1:]])
S_full   = np.concatenate([S_before,   S_sw[1:]])
TOL_full = np.concatenate([TOL_before, TOL_sw[1:]])
R_full   = np.concatenate([R_before,   R_sw[1:]])


plt.plot(T_full, N_full, color='black', linestyle='--',
         label="Сценарий: смена терапии после t_min", alpha=0.4)
plt.plot(T_full, R_full, color='black', linestyle='--',
         label="Сценарий: смена терапии после t_min толерантные", alpha=0.4)
plt.plot(T_full, S_full, color='black', linestyle='--',
         label="Сценарий: смена терапии после t_min чувствительные", alpha=0.4)
plt.plot(T_full, TOL_full, color='black', linestyle='--',
         label="Сценарий: смена терапии после t_min резистентные", alpha=0.4)
plt.title("S–T–R модель опухоли с возможной сменой терапии после минимума")
plt.xlabel("Месяцы")
plt.ylabel("Объём опухоли")
plt.grid(alpha=0.3)
plt.legend(fontsize=7)
plt.tight_layout()
plt.show()


# ===== 5. Сообщение врачу о привыкании клеточной популяции к препарату =====
months = int(t_min)
fraction = t_min - months
weeks = fraction * 4.345    
weeks_rounded = int(round(weeks))

if Ntot_dense[-1] > Ntot_dense[idx_min]:
    message_to_doctor = f"""===ALERT===\n
У пациента: id45012 есть тенденция к росту опухолевой массы — возможная
резистентность через {months} месяцев и {weeks_rounded} недели.
Рекомендуется рассмотреть смену терапии.\n
==========="""
else:
    message_to_doctor = "Опухоль продолжает уменьшаться или стабилизирована."

print(message_to_doctor)

stage_metrics = pd.DataFrame(all_stage_metrics)
stage_metrics