package com.example.payment;

import java.util.List;
import java.util.Optional;
import com.stripe.api.StripeGateway;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Payment service handling payment processing
 */
@Service
@Transactional
public class PaymentService extends BaseService implements PaymentProcessor {

    private final StripeGateway stripeGateway;
    private static final int MAX_RETRIES = 3;

    public PaymentService(StripeGateway stripeGateway) {
        this.stripeGateway = stripeGateway;
    }

    /**
     * Process payment for an order
     */
    @Override
    @Transactional(rollbackFor = PaymentException.class)
    public PaymentResult processPayment(Order order) throws PaymentException {
        validateOrder(order);

        try {
            ChargeResult result = chargeCard(order.getAmount(), order.getCardToken());
            saveTransaction(result);
            return new PaymentResult(result.getId(), true);

        } catch (StripeTimeoutException e) {
            logError("Stripe timeout", e);
            throw new PaymentException("Payment gateway timeout", e);

        } catch (InsufficientFundsException e) {
            logError("Insufficient funds", e);
            return new PaymentResult(null, false);

        } catch (Exception e) {
            logError("Unexpected error", e);
            throw new PaymentException("Payment processing failed", e);
        }
    }

    private void validateOrder(Order order) throws ValidationException {
        if (order == null) {
            throw new ValidationException("Order cannot be null");
        }
        if (order.getAmount() <= 0) {
            throw new ValidationException("Amount must be positive");
        }
    }

    private ChargeResult chargeCard(double amount, String cardToken)
            throws StripeTimeoutException, InsufficientFundsException {
        return stripeGateway.charge(amount, cardToken);
    }

    private void saveTransaction(ChargeResult result) {
        // Save to database
    }

    private void logError(String message, Exception e) {
        System.err.println(message + ": " + e.getMessage());
    }

    public static void main(String[] args) {
        System.out.println("Payment Service Started");
    }
}