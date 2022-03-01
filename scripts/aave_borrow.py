import web3
from scripts.get_weth import get_weth
from scripts.helpful_scripts import get_account
from brownie import config, network, interface
from web3 import Web3
import time

# 0.1
AMOUNT = Web3.toWei(0.01, "ether")


def main():
    account = get_account()
    erc20_address = config["networks"][network.show_active()]["weth_token"]
    if network.show_active() in ["mainnet-fork"]:
        get_weth()
    lending_pool = get_lending_pool()
    approve_tx = approve_erc20(AMOUNT, lending_pool.address, erc20_address, account)
    print("Depositing...")
    tx = lending_pool.deposit(
        erc20_address, AMOUNT, account.address, 0, {"from": account}
    )
    tx.wait(1)
    print("Deposited!")

    borrowable_eth, total_debt = get_borrowable_data(lending_pool, account)

    print("Let's borrow!")

    # DAI in terms os ETH
    dai_eth_price_feed = config["networks"][network.show_active()]["dai_eth_price_feed"]
    dai_eth_price = get_asset_price(dai_eth_price_feed)

    amount_dai_to_borrow = (1 / dai_eth_price) * (borrowable_eth * 0.95)
    # borrowable_eth -> borrowable_dai * 95%
    print(f"we are going to borrow {amount_dai_to_borrow} DAI")

    dai_address = config["networks"][network.show_active()]["dai_token"]
    borrow_tx = lending_pool.borrow(
        dai_address,
        Web3.toWei(amount_dai_to_borrow, "ether"),
        1,
        0,
        account.address,
        {"from": account},
    )
    borrow_tx.wait(1)

    print("we borrowed some DAI!")

    get_borrowable_data(lending_pool, account)

    repay_all(amount_dai_to_borrow, lending_pool, account)

    print("You just deposited, borrowed, and repayed with Aave, Brownie and Chainlink")


def repay_all(amount, lending_pool, account):
    asset = config["networks"][network.show_active()]["dai_token"]
    approve_erc20(Web3.toWei(amount, "ether"), lending_pool, asset, account)

    repay_tx = lending_pool.repay(asset, amount, 1, account.address, {"from": account})
    repay_tx.wait(1)
    print("Repaid")


def get_borrowable_data(lending_pool, account):
    (
        total_collateral_eth,
        total_debt_eth,
        available_borrow_eth,
        current_liquidation_threshold,
        ltv,
        health_factor,
    ) = lending_pool.getUserAccountData(account.address)

    available_borrow_eth = Web3.fromWei(available_borrow_eth, "ether")
    total_debt_eth = Web3.fromWei(total_debt_eth, "ether")
    total_collateral_eth = Web3.fromWei(total_collateral_eth, "ether")

    print(f"you have {total_collateral_eth} worth of ETH deposited")
    print(f"you have {total_debt_eth} worth of ETH borrowed")
    print(f"you can borrow {available_borrow_eth} worth of ETH")

    return (float(available_borrow_eth), float(total_debt_eth))


def get_asset_price(dai_eth_price_feed):
    dai_eth_price_feed = interface.AggregatorV3Interface(dai_eth_price_feed)
    latest_price = dai_eth_price_feed.latestRoundData()[1]
    covertedPrice = Web3.fromWei(latest_price, "ether")
    print(f"DAI/ETH price is {covertedPrice}")
    return float(covertedPrice)


def get_lending_pool():
    lending_pool_addresses_provider = interface.ILendingPoolAddressesProvider(
        config["networks"][network.show_active()]["lending_pool_addresses_provider"]
    )
    lending_pool_address = lending_pool_addresses_provider.getLendingPool()
    lending_pool = interface.ILendingPool(lending_pool_address)
    return lending_pool


def approve_erc20(amount, spender, erc20_address, account):
    print("Approving ERC20 token...")
    erc20 = interface.IERC20(erc20_address)
    tx = erc20.approve(spender, amount, {"from": account})
    tx.wait(1)
    print("Approved!")
    return tx
