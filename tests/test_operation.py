import brownie
import pytest
from brownie import Contract, Wei


def test_operation(
    chain,
    vaultA,
    vaultB,
    tokenA,
    tokenB,
    providerA,
    providerB,
    joint,
    gov,
    strategist,
    tokenA_whale,
    tokenB_whale,
):

    tokenA.approve(vaultA, 2 ** 256 - 1, {"from": tokenA_whale})
    vaultA.deposit({"from": tokenA_whale})

    tokenB.approve(vaultB, 2 ** 256 - 1, {"from": tokenB_whale})
    vaultB.deposit({"from": tokenB_whale})

    # https://www.coingecko.com/en/coins/fantom
    tokenA_price = 0.45
    # https://www.coingecko.com/en/coins/popsicle-finance
    tokenB_price = 3.68
    usd_amount = Wei("1000 ether")

    vaultA.updateStrategyMaxDebtPerHarvest(
        providerA, usd_amount // tokenA_price, {"from": vaultA.governance()}
    )
    vaultB.updateStrategyMaxDebtPerHarvest(
        providerB, usd_amount // tokenB_price, {"from": vaultB.governance()}
    )

    providerA.harvest({"from": strategist})
    providerB.harvest({"from": strategist})
    assert joint.balanceOfA() * usd_amount > Wei("990 ether")
    assert joint.balanceOfB() * usd_amount > Wei("990 ether")

    print(f"Joint has {joint.balanceOfA()/1e18} wftm and {joint.balanceOfB()/1e18} ice")
    joint.harvest({"from": strategist})
    assert joint.balanceOfStake() > 0

    # Wait plz
    chain.sleep(60 * 60 * 24 * 5)
    chain.mine(50)

    # If there is any profit it should go to the providers
    assert joint.pendingReward() > 0
    # If joint doesn't reinvest, and providers do not invest want, the want
    # will stay in the providers
    joint.setReinvest(False, {"from": strategist})
    providerA.setInvestWant(False, {"from": strategist})
    providerB.setInvestWant(False, {"from": strategist})
    joint.harvest({"from": strategist})
    assert providerA.balanceOfWant() > 0
    assert providerB.balanceOfWant() > 0

    # Harvest should be a no-op
    providerA.harvest({"from": strategist})
    providerB.harvest({"from": strategist})
    chain.sleep(60 * 60 * 8)
    chain.mine(1)
    assert providerA.balanceOfWant() > 0
    assert providerB.balanceOfWant() > 0
    assert vaultA.strategies(providerA).dict()["totalGain"] == 0
    assert vaultB.strategies(providerB).dict()["totalGain"] == 0

    # Liquidate position and make sure capital + profit is back
    joint.liquidatePosition({"from": strategist})
    print(
        f"After liquidation, Joint has {joint.balanceOfA()/1e18} wftm and {joint.balanceOfB()/1e18} ice"
    )
    print(f"ProviderA: {providerA.balanceOfWant()/1e18}")
    print(f"ProviderB: {providerB.balanceOfWant()/1e18}")
    providerA.setTakeProfit(True, {"from": strategist})
    providerB.setTakeProfit(True, {"from": strategist})
    providerA.setInvestWant(False, {"from": strategist})
    providerB.setInvestWant(False, {"from": strategist})

    joint.harvest({"from": strategist})
    assert providerA.balanceOfWant() > 0
    assert providerB.balanceOfWant() > 0

    providerA.harvest({"from": strategist})
    providerB.harvest({"from": strategist})
    chain.sleep(60 * 60 * 8)
    chain.mine(1)
    assert vaultA.strategies(providerA).dict()["totalGain"] > 0
    assert vaultB.strategies(providerB).dict()["totalGain"] > 0

    print(f"wFTM profit: {vaultA.strategies(providerA).dict()['totalGain']/1e18} wftm")
    print(f"ice profit: {vaultB.strategies(providerB).dict()['totalGain']/1e18} ice")
