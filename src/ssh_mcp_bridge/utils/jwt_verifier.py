"""JWT token verification for Auth0."""

import logging
from typing import Optional, Dict, Any
import httpx
import jwt
from jwt import PyJWKClient
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class JWTVerifier:
    """JWT token verifier for Auth0 tokens."""

    def __init__(
        self,
        issuer: str,
        audience: str,
        jwks_uri: Optional[str] = None,
    ):
        """Initialize JWT verifier.

        Args:
            issuer: The Auth0 issuer URL (e.g., https://your-domain.auth0.com/)
            audience: The API audience/identifier
            jwks_uri: Optional JWKS URI (defaults to issuer + .well-known/jwks.json)
        """
        self.issuer = issuer.rstrip("/") + "/"
        self.audience = audience
        
        # Set JWKS URI
        if jwks_uri:
            self.jwks_uri = jwks_uri
        else:
            self.jwks_uri = f"{self.issuer}.well-known/jwks.json"
        
        self.jwks_client = PyJWKClient(self.jwks_uri)
        logger.info(f"JWT Verifier initialized - Issuer: {self.issuer}, Audience: {self.audience}")

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token and return claims.

        Args:
            token: The JWT token string

        Returns:
            Dictionary of token claims

        Raises:
            HTTPException: If token is invalid
        """
        try:
            # Get signing key from JWKS
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            
            # Decode and verify token
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
            )
            
            logger.debug(f"Token verified for user: {payload.get('sub')}")
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": 'Bearer error="invalid_token", error_description="The access token expired"'},
            )
        except jwt.InvalidAudienceError:
            logger.warning(f"Invalid audience in token. Expected: {self.audience}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token audience",
                headers={"WWW-Authenticate": 'Bearer error="invalid_token", error_description="Invalid audience"'},
            )
        except jwt.InvalidIssuerError:
            logger.warning(f"Invalid issuer in token. Expected: {self.issuer}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token issuer",
                headers={"WWW-Authenticate": 'Bearer error="invalid_token", error_description="Invalid issuer"'},
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": 'Bearer error="invalid_token", error_description="Invalid token"'},
            )
        except Exception as e:
            logger.error(f"Error verifying token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token verification failed",
                headers={"WWW-Authenticate": 'Bearer error="invalid_token", error_description="Token verification failed"'},
            )

    def get_user_info(self, claims: Dict[str, Any]) -> Dict[str, str]:
        """Extract user information from token claims.

        Args:
            claims: Token claims dictionary

        Returns:
            Dictionary with user information
        """
        # Extract custom claims (namespaced)
        namespace = self.audience
        
        return {
            "user_id": claims.get(f"{namespace}/user_id", claims.get("sub")),
            "email": claims.get(f"{namespace}/email", claims.get("email", "")),
            "name": claims.get(f"{namespace}/name", claims.get("name", "")),
        }
